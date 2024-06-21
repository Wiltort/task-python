from typing import List
from datetime import datetime, timezone, timedelta
from sqlalchemy import ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app import db


class Service(db.Model):
    __tablename__ = 'service'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(64), index=True, unique=True)
    description: Mapped[str] = mapped_column(Text)

    statuses: Mapped[List["Status"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return '<Service {}>'.format(self.name)

    def actual_status(self):
        data = {
            'name': self.name,
            'status': self.statuses[-1].name,
            'description': self.description}
        return data

    def from_dict(self, data, new_service=False):
        for field in ['name', 'description']:
            if field in data:
                setattr(self, field, data[field])
        if new_service:
            if 'status' in data:
                s = Status(name=data['status'])
                self.statuses.append(s)
        else:
            if 'status' in data:
                name = data['status']
                if name != self.statuses[-1].name:
                    s = Status(name=data['status'])
                    self.statuses.append(s)

    @staticmethod
    def all_services():
        services = Service.query.all()
        data = {
            'items': [item.actual_status() for item in services]
        }
        return data

    def statuses_to_dict(self):
        data = [item.to_dict() for item in self.statuses]
        return data

    def get_sla(self, from_dt, to_dt):
        statuses_list = self.statuses
        history = []
        total_time = to_dt - from_dt
        not_working_time = timedelta(seconds=0)
        data = {'not_working_time': f'{not_working_time.total_seconds()} s', 'sla': '0.000 %'}
        left = {}
        for i, st in enumerate(statuses_list):
            if st.updated_at <= from_dt:
                left = {'index': i, 'status': st.name, 'dt': st.updated_at}
            if st.updated_at > from_dt and st.updated_at < to_dt:
                history.append(
                    {'index': i, 'status': st.name, 'dt': st.updated_at})
            if st.updated_at >= to_dt:
                break
        if not history:
            if left != {}:
                if left['status'] == 'out of service':
                    data['not_working_time'] = f'{total_time.total_seconds()} s'
                    return data
                data['sla'] = '100.000 %'
                return data
            data['not_working_time'] = f'{total_time.total_seconds()} s'
            return data

        if left != {}:
            current_status = left
        else:
            current_status = {'index': None,
                              'status': 'out of service', 'dt': from_dt}
        for item in history:
            if current_status['status'] == 'out of service':
                not_working_time += item['dt'] - current_status['dt']
            current_status = item
        if current_status['status'] == 'out of service':
            not_working_time += to_dt - current_status['dt']
        sla = "{:.3f}".format((total_time.total_seconds(
        )-not_working_time.total_seconds())/total_time.total_seconds()*100)+" %"
        data['sla'] = sla
        data['not_working_time'] = f'{not_working_time.total_seconds()} s'
        return data


class Status(db.Model):
    __tablename__ = "status"

    id: Mapped[int] = mapped_column(primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    name: Mapped[str] = mapped_column(String(32), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"))

    service: Mapped[Service] = relationship(back_populates='statuses')

    def to_dict(self):
        data = {
            'name': self.name,
            'updated_at': self.updated_at.isoformat()+'Z'
        }
        return data

    def __repr__(self):
        return '<Status {}>'.format(self.name)
