from app.api import bp
from flask import jsonify, request
from app.models import Service
from app.api.errors import bad_request
from app import db
import datetime as dt


@bp.route('/services/<int:id>', methods=['GET'])
def get_statuses(id):
    '''
    По имени сервиса выдает историю изменения 
    состояния и все данные по каждому состоянию
    '''
    return jsonify(Service.query.get_or_404(id).statuses_to_dict())


@bp.route('/services', methods=['GET'])
def get_services():
    '''
    Выводит список сервисов с актуальным состоянием
    '''
    return jsonify(Service.all_services())


@bp.route('/services/<int:id>/sla', methods=['GET'])
def get_sla(id):
    '''
    По указанному интервалу выдается информация 
    о том сколько не работал сервис и считать SLA
    в процентах до 3-й запятой
    '''
    from_str = request.args.get('from_dt', type=str)
    to_str = request.args.get('to_dt', type=str)
    service = Service.query.get_or_404(id)
    try:
        from_dt = dt.datetime.strptime(from_str, '%Y-%m-%d %H:%M:%S')
        to_dt = dt.datetime.strptime(to_str, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return bad_request('use ISO 8601 for datetime objects: "%Y-%m-%d %H:%M:%S"')
    return jsonify(service.get_sla(from_dt=from_dt, to_dt=to_dt))

@bp.route('/services', methods=['POST'])
def create_service():
    '''
    Получает и сохраняет данные: имя, состояние, описание
    '''
    data = request.get_json() or {}
    if 'name' not in data or 'status' not in data or 'description' not in data:
        return bad_request('must include name, status and description')
    if Service.query.filter_by(name=data['name']).first():
        return bad_request('please use a different name')
    if data['status'] not in ['out of service', 'online', 'unstable']:
        return bad_request('status must be one of "out of service", "online", "unstable"')
    service = Service()
    service.from_dict(data=data, new_service=True)
    db.session.add(service)
    db.session.commit()
    response = jsonify(service.actual_status())
    response.status_code = 201
    return response


@bp.route('/services/<int:id>', methods=['PUT'])
def update_service(id):
    '''
    обновление статуса
    '''
    service = Service.query.get_or_404(id)
    data = request.get_json() or {}
    if 'name' in data and data['name'] != service.name and \
            Service.query.filter_by(name=data['name']).first():
        return bad_request('please use a different name')
    if 'status' in data and data['status'] == service.statuses[-1].name:
        return bad_request('status is not changed')
    if 'status' in data and data['status'] not in ['out of service', 'online', 'unstable']:
        return bad_request('status must be one of "out of service", "online", "unstable"')
    service.from_dict(data, new_service=False)
    db.session.commit()
    return jsonify(service.actual_status())
