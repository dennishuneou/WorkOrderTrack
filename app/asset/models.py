from app import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    asset_name = db.Column(db.String(100), nullable=False, index=True)
    person_name = db.Column(db.String(100))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))

    def __init__(self, type, asset_name, person_name, start_time, end_time, status):
        self.type = type
        self.asset_name = asset_name
        self.person_name = person_name
        self.start_time = start_time
        self.end_time = end_time
        self.status = status

    def __repr__(self):
        return '{} by {}'.format(self.asset_name, self.person_name)

class WorkOrder(db.Model):
    __tablename__ = 'workorder'

    id = db.Column(db.Integer, primary_key=True)
    wo = db.Column(db.String(100), nullable=False)
    customers = db.Column(db.String(100), nullable=False)
    pn = db.Column(db.String(100), nullable=False)
    csn = db.Column(db.String(100), nullable=False)
    asid = db.Column(db.Integer, nullable=True)
    insid=db.Column(db.Integer, nullable=True)
    astime=db.Column(db.DateTime, nullable=True)
    intime=db.Column(db.DateTime, nullable=True)
    status =db.Column(db.Integer, nullable=True)
     
    def __init__(self, wo, customers, pn, csn, asid, insid,astime, intime, status):
        self.wo = wo
        self.customers = customers
        self.pn = pn
        self.csn = csn
        self.asid = asid
        self.insid = insid
        self.astime = astime
        self.intime = intime
        self.status = status

    def __repr__(self):
        return '{} by {}'.format(self.wo)

class Production(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    wo = db.Column(db.String(100), nullable=False)
    pn = db.Column(db.String(100), nullable=False)
    csn = db.Column(db.String(100), nullable=False)
    msn = db.Column(db.String(100), nullable=False)
    cpu = db.Column(db.String(100), nullable=True)
    mem1= db.Column(db.String(256), nullable=True)
    mem2= db.Column(db.String(256), nullable=True)
    mem3= db.Column(db.String(256), nullable=True)
    mem4= db.Column(db.String(256), nullable=True)
    gpu1= db.Column(db.String(100), nullable=True)
    gpu2= db.Column(db.String(100), nullable=True)
    sata1= db.Column(db.String(100), nullable=True)
    sata2= db.Column(db.String(100), nullable=True)
    sata3= db.Column(db.String(100), nullable=True)
    sata4= db.Column(db.String(100), nullable=True)
    m21= db.Column(db.String(100), nullable=True)
    m22= db.Column(db.String(100), nullable=True)
    wifi= db.Column(db.String(100), nullable=True)
    fg5g= db.Column(db.String(100), nullable=True)
    can= db.Column(db.String(100), nullable=True)
    other= db.Column(db.String(100), nullable=True)
    note= db.Column(db.String(256), nullable=True)
    report=db.Column(db.String(512000), nullable=False)
     
    def __init__(self, wo, pn, csn, msn, cpu, mem1, mem2,mem3, mem4, gpu1, gpu2, sata1, sata2, sata3, sata4, m21, m22, wifi, fg5g, can, other, note, report):
        self.wo = wo
        self.pn = pn
        self.csn = csn
        self.msn = msn
        self.cpu = cpu
        self.mem1 = mem1
        self.mem2 = mem2
        self.mem3 = mem3
        self.mem4 = mem4
        self.gpu1 = gpu1
        self.gpu2 = gpu2
        self.sata1 = sata1
        self.sata2 = sata2
        self.sata3 = sata3
        self.sata4 = sata4
        self.m21 = m21
        self.m22 = m22
        self.wifi = wifi
        self.fg5g = fg5g
        self.can = can
        self.other = other
        self.note = note
        self.report = report



    def __repr__(self):
        return '{} by {}'.format(self.wo)