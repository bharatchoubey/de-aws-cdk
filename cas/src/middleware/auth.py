from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from src.models.user import User

def jwt_required_with_user():
    """Decorator that requires JWT token and returns current user"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                
                if not current_user:
                    return jsonify({'message': 'User not found'}), 404
                
                # Add current_user to kwargs
                kwargs['current_user'] = current_user
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'message': 'Invalid token'}), 401
        
        return decorated_function
    return decorator

def admin_required():
    """Decorator that requires admin privileges (for future use)"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user_id = get_jwt_identity()
            current_user = User.query.get(current_user_id)
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 404
            
            # For now, all authenticated users are considered admins
            # In future, add role field to User model
            kwargs['current_user'] = current_user
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
