from flask import Blueprint, request, jsonify
from src.models.configuration import Configuration, ConfigType
from src.models.user import User
from src.database import db
from src.middleware.auth import jwt_required_with_user

configs_bp = Blueprint('configs', __name__, url_prefix='/api/configs')

@configs_bp.route('', methods=['POST'])
@jwt_required_with_user()
def create_configuration(current_user):
    """Create a new configuration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['app_name', 'config_type', 'environment', 'key', 'value']
        for field in required_fields:
            if not data or not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400
        
        app_name = data['app_name'].strip()
        config_type_str = data['config_type'].strip().lower()
        environment = data['environment'].strip().lower()
        key = data['key'].strip()
        value = data['value']
        description = data.get('description', '').strip()
        
        # Validate config_type
        try:
            config_type = ConfigType(config_type_str)
        except ValueError:
            return jsonify({
                'message': 'Invalid config_type. Must be "application" or "infrastructure"'
            }), 400
        
        # Validate environment
        valid_environments = ['dev', 'development', 'staging', 'prod', 'production']
        if environment not in valid_environments:
            return jsonify({
                'message': f'Invalid environment. Must be one of: {", ".join(valid_environments)}'
            }), 400
        
        # Check if configuration already exists
        existing_config = Configuration.query.filter_by(
            app_name=app_name,
            environment=environment,
            key=key
        ).first()
        
        if existing_config:
            return jsonify({
                'message': f'Configuration already exists for {app_name}:{environment}:{key}'
            }), 409
        
        # Create new configuration
        config = Configuration(
            app_name=app_name,
            config_type=config_type,
            environment=environment,
            key=key,
            value=str(value),  # Convert to string for storage
            description=description,
            created_by_id=current_user.id
        )
        
        db.session.add(config)
        db.session.commit()
        
        return jsonify({
            'message': 'Configuration created successfully',
            'configuration': config.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to create configuration', 'error': str(e)}), 500

@configs_bp.route('', methods=['GET'])
@jwt_required_with_user()
def list_configurations(current_user):
    """List all configurations with optional filters"""
    try:
        # Get query parameters for filtering
        app_name = request.args.get('app_name')
        config_type = request.args.get('config_type')
        environment = request.args.get('environment')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Build query
        query = Configuration.query
        
        if app_name:
            query = query.filter(Configuration.app_name.ilike(f'%{app_name}%'))
        
        if config_type:
            try:
                config_type_enum = ConfigType(config_type.lower())
                query = query.filter(Configuration.config_type == config_type_enum)
            except ValueError:
                return jsonify({'message': 'Invalid config_type filter'}), 400
        
        if environment:
            query = query.filter(Configuration.environment == environment.lower())
        
        # Pagination
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        configurations = [config.to_dict() for config in pagination.items]
        
        return jsonify({
            'configurations': configurations,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to list configurations', 'error': str(e)}), 500

@configs_bp.route('/<int:config_id>', methods=['GET'])
@jwt_required_with_user()
def get_configuration(current_user, config_id):
    """Get a specific configuration by ID"""
    try:
        config = Configuration.query.get(config_id)
        
        if not config:
            return jsonify({'message': 'Configuration not found'}), 404
        
        return jsonify({'configuration': config.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get configuration', 'error': str(e)}), 500

@configs_bp.route('/<int:config_id>', methods=['PUT'])
@jwt_required_with_user()
def update_configuration(current_user, config_id):
    """Update a configuration"""
    try:
        config = Configuration.query.get(config_id)
        
        if not config:
            return jsonify({'message': 'Configuration not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Update fields if provided
        if 'app_name' in data:
            config.app_name = data['app_name'].strip()
        
        if 'config_type' in data:
            try:
                config.config_type = ConfigType(data['config_type'].strip().lower())
            except ValueError:
                return jsonify({
                    'message': 'Invalid config_type. Must be "application" or "infrastructure"'
                }), 400
        
        if 'environment' in data:
            environment = data['environment'].strip().lower()
            valid_environments = ['dev', 'development', 'staging', 'prod', 'production']
            if environment not in valid_environments:
                return jsonify({
                    'message': f'Invalid environment. Must be one of: {", ".join(valid_environments)}'
                }), 400
            config.environment = environment
        
        if 'key' in data:
            config.key = data['key'].strip()
        
        if 'value' in data:
            config.value = str(data['value'])
        
        if 'description' in data:
            config.description = data['description'].strip()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'configuration': config.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update configuration', 'error': str(e)}), 500

@configs_bp.route('/<int:config_id>', methods=['DELETE'])
@jwt_required_with_user()
def delete_configuration(current_user, config_id):
    """Delete a configuration"""
    try:
        config = Configuration.query.get(config_id)
        
        if not config:
            return jsonify({'message': 'Configuration not found'}), 404
        
        db.session.delete(config)
        db.session.commit()
        
        return jsonify({'message': 'Configuration deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete configuration', 'error': str(e)}), 500
