from app import db
from datetime import datetime
class PnMap(db.Model):
    __tablename__ = 'pnmap'

    id = db.Column(db.Integer, primary_key=True)
    pn = db.Column(db.String(100), nullable=False)
    biosv = db.Column(db.String(100), nullable=False)
    prefix = db.Column(db.String(20), nullable=False)
    net = db.Column(db.Integer, nullable=False)
    poe = db.Column(db.Integer, nullable=False)
    ign = db.Column(db.Integer, nullable=False)
    
    def __init__(self, pn, biosv,prefix, net, poe, ign):
        self.pn = pn
        self.biosv = biosv
        self.pn = pn
        self.prefix = prefix
        self.net = net
        self.poe = poe
        self.ign = ign

class WorkOrder(db.Model):
    __tablename__ = 'workorder'

    id = db.Column(db.Integer, primary_key=True)
    wo = db.Column(db.String(100), nullable=False)
    customers = db.Column(db.String(100), nullable=False)
    pn = db.Column(db.String(100), nullable=False)
    csn = db.Column(db.String(100), nullable=False)
    cputype =  db.Column(db.String(100), nullable=True)
    memorysize =  db.Column(db.String(100), nullable=True)
    disksize =  db.Column(db.String(100), nullable=True)
    cpuinstall = db.Column(db.Boolean, nullable=True)
    memoryinstall = db.Column(db.Boolean, nullable=True)
    gpuinstall = db.Column(db.Boolean, nullable=True)
    wifiinstall = db.Column(db.Boolean, nullable=True)
    caninstall = db.Column(db.Boolean, nullable=True)
    mezioinstall = db.Column(db.Boolean, nullable=True)
    fg5ginstall = db.Column(db.Boolean, nullable=True)
    osinstall = db.Column(db.String(40), nullable=True)
    packgo = db.Column(db.Boolean, nullable=True)
    asid = db.Column(db.Integer, nullable=True)
    insid=db.Column(db.Integer, nullable=True)
    tktime=db.Column(db.DateTime, nullable=True)
    astime=db.Column(db.DateTime, nullable=True)
    intime=db.Column(db.DateTime, nullable=True)
    status =db.Column(db.Integer, nullable=True)
    csid=db.Column(db.Integer, nullable=True)
    cstime=db.Column(db.DateTime, nullable=True)
    ldtime=db.Column(db.DateTime, nullable=True)

    def __init__(self, wo, customers, pn, csn, cputype, memorysize, disksize, cpuinstall, memoryinstall, gpuinstall,  wifiinstall, caninstall, mezioinstall, fg5ginstall, osinstall, packgo, asid, insid,astime, intime, csid, cstime, tktime, ldtime, status):
        self.wo = wo
        self.customers = customers
        self.pn = pn
        self.csn = csn
        self.cputype = cputype
        self.memorysize = memorysize
        self.disksize = disksize
        self.cpuinstall = cpuinstall
        self.memoryinstall = memoryinstall
        self.gpuinstall = gpuinstall
        self.wifiinstall = wifiinstall
        self.caninstall = caninstall
        self.mezioinstall = mezioinstall
        self.fg5ginstall = fg5ginstall
        self.osinstall = osinstall
        self.packgo = packgo
        self.asid = asid
        self.insid = insid
        self.tktime = tktime
        self.astime = astime
        self.intime = intime
        self.csid = csid
        self.cstime = cstime
        self.ldtime = ldtime
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