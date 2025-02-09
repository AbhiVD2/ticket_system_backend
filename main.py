from bson import ObjectId
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# MongoDB setup (replace the URI if needed)
app.config["MONGO_URI"] = "mongodb://localhost:27017/ticket_system"
mongo = PyMongo(app)

# Collection references
societyData = mongo.db.societyData
managers = mongo.db.managers
deleted_managers = mongo.db.deleted_managers
users_collection = mongo.db.users
deleted_users_collection = mongo.db.deleted_users
ticketdata = mongo.db.tickets

# Helper function to convert ObjectId to string
def objectid_to_str(record):
    if '_id' in record:
        record['_id'] = str(record['_id'])
    return record


# Societies Routes

@app.route('/api/societies', methods=['GET'])
def get_societies():
    society_list = [objectid_to_str(society) for society in societyData.find()]
    return jsonify(society_list)

@app.route('/api/societies', methods=['POST'])
def add_society():
    data = request.json
    new_society = {
        "name": data.get('name'),
        "address": data.get('address'),
        "incharge": data.get('incharge'),
        "contact": data.get('contact')
    }
    result = societyData.insert_one(new_society)
    return jsonify({"message": "Society added", "id": str(result.inserted_id)}), 201

@app.route('/api/societies/<society_id>', methods=['PUT'])
def update_society(society_id):
    data = request.json
    updated_data = {
        "name": data.get('name'),
        "address": data.get('address'),
        "incharge": data.get('incharge'),
        "contact": data.get('contact')
    }
    societyData.update_one({'_id': ObjectId(society_id)}, {'$set': updated_data})
    return jsonify({"message": "Society updated successfully"})

@app.route('/api/societies/<society_id>', methods=['DELETE'])
def delete_society(society_id):
    societyData.delete_one({'_id': ObjectId(society_id)})
    return jsonify({"message": "Society deleted successfully"})


# Manager Routes

@app.route('/api/managers', methods=['GET'])
def get_managers():
    managers1 = [objectid_to_str(manager) for manager in managers.find()]
    return jsonify(managers1)

@app.route('/api/managers', methods=['POST'])
def add_manager():
    data = request.json
    result = managers.insert_one(data)
    return jsonify({'message': 'Manager added successfully', 'id': str(result.inserted_id)}), 201

@app.route('/api/managers/<manager_id>', methods=['PUT'])
def update_manager(manager_id):
    updated_manager = request.json
    result = managers.update_one({'_id': ObjectId(manager_id)}, {'$set': updated_manager})
    if result.matched_count:
        return jsonify({"message": "Manager updated successfully!"})
    return jsonify({"message": "Manager not found!"}), 404

@app.route('/api/managers/<manager_id>', methods=['DELETE'])
def delete_manager(manager_id):
    manager = managers.find_one({'_id': ObjectId(manager_id)})
    if manager:
        manager['deletedAt'] = datetime.utcnow()
        deleted_managers.insert_one(manager)
        managers.delete_one({'_id': ObjectId(manager_id)})
        return jsonify({"message": "Manager deleted successfully!"})
    return jsonify({"message": "Manager not found!"}), 404


@app.route('/api/managers/restore/<manager_id>', methods=['POST'])
def restore_manager(manager_id):
    manager = deleted_managers.find_one({'_id': ObjectId(manager_id)})
    if manager:
        del manager['deletedAt']
        managers.insert_one(manager)
        deleted_managers.delete_one({'_id': ObjectId(manager_id)})
        return jsonify({"message": "Manager restored successfully!"})
    return jsonify({"message": "Manager not found!"}), 404

@app.route('/api/managers/permanent_delete/<manager_id>', methods=['DELETE'])
def permanently_delete_manager(manager_id):
    result = deleted_managers.delete_one({'_id': ObjectId(manager_id)})
    if result.deleted_count:
        return jsonify({"message": "Manager permanently deleted!"})
    return jsonify({"message": "Manager not found!"}), 404

@app.route('/api/deleted_managers', methods=['GET'])
def get_deleted_managers():
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    deleted_managers_list = list(deleted_managers.find({'deletedAt': {'$gt': one_month_ago}}))
    return jsonify([objectid_to_str(manager) for manager in deleted_managers_list])


# Users Routes

@app.route('/api/users', methods=['GET'])
def get_users():
    active_users = [objectid_to_str(user) for user in users_collection.find({"deletedAt": {"$exists": False}})]
    return jsonify(active_users)

@app.route('/api/users', methods=['POST'])
def update_user():
    data = request.json
    user_id = data.get('_id')
    updated_data = {key: value for key, value in data.items() if key != '_id'}
    
    result = users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': updated_data})
    
    if result.matched_count:
        return jsonify({"message": "User updated successfully!"})
    return jsonify({"message": "User not found!"}), 404

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if user:
        user['deletedAt'] = datetime.utcnow()
        deleted_users_collection.insert_one(user)
        users_collection.delete_one({'_id': ObjectId(user_id)})
        return jsonify({"message": "User soft deleted successfully!"})
    return jsonify({"message": "User not found!"}), 404

@app.route('/api/users/restore/<user_id>', methods=['POST'])
def restore_user(user_id):
    deleted_user = deleted_users_collection.find_one({'_id': ObjectId(user_id)})
    if deleted_user:
        del deleted_user['deletedAt']
        users_collection.insert_one(deleted_user)
        deleted_users_collection.delete_one({'_id': ObjectId(user_id)})
        return jsonify({"message": "User restored successfully!"})
    return jsonify({"message": "User not found!"}), 404

@app.route('/api/users/permanent/<user_id>', methods=['DELETE'])
def permanently_delete_user(user_id):
    result = deleted_users_collection.delete_one({'_id': ObjectId(user_id)})
    if result.deleted_count:
        return jsonify({"message": "User permanently deleted!"})
    return jsonify({"message": "User not found!"}), 404

@app.route('/api/deleted-users', methods=['GET'])
def get_deleted_users():
    deleted_users = [objectid_to_str(user) for user in deleted_users_collection.find()]
    return jsonify(deleted_users)

@app.route('/api/deleted-users/cleanup', methods=['DELETE'])
def clean_up_deleted_users():
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    deleted_users_collection.delete_many({'deletedAt': {'$lt': one_month_ago.isoformat()}})
    return jsonify({"message": "Deleted users older than one month have been removed."})

@app.route('/api/deleted_managers/<manager_id>/restore', methods=['PUT'])
def api_restore_manager(manager_id):
    try:
        # Find the manager in the deleted managers collection
        manager = deleted_managers.find_one({'_id': ObjectId(manager_id)})
        
        if not manager:
            return jsonify({"message": "Manager not found!"}), 404
        
        # Remove the 'deletedAt' field to restore the manager
        del manager['deletedAt']
        
        # Insert the manager back into the managers collection
        managers.insert_one(manager)
        
        # Remove the manager from the deleted managers collection
        deleted_managers.delete_one({'_id': ObjectId(manager_id)})
        
        return jsonify({"message": "Manager restored successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# 

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    tickets = ticketdata.find()
    ticket_list = []
    for ticket in tickets:
        ticket['_id'] = str(ticket['_id'])
        ticket_list.append(ticket)
    return jsonify(ticket_list)

@app.route('/api/tickets', methods=['POST'])
def add_ticket():
    ticket = request.json
    ticketdata.insert_one(ticket)
    return jsonify({"message": "Ticket added successfully!"}), 201

@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    updated_ticket = request.json
    ticketdata.update_one({'_id': ObjectId(ticket_id)}, {'$set': updated_ticket})
    return jsonify({"message": "Ticket updated successfully!"})

@app.route('/api/tickets/<ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    ticketdata.delete_one({'_id': ObjectId(ticket_id)})
    return jsonify({"message": "Ticket deleted successfully!"})







if __name__ == '__main__':
    app.run(debug=True)
