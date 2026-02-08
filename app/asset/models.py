from app import db
from datetime import datetime
#Add models here
## BOX, limitweight

class PackageBox(db.Model):
    __tablename__ = 'packagebox'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    abbreviation = db.Column(db.String(32), nullable=True)
    height = db.Column(db.REAL, nullable=False)
    width = db.Column(db.REAL, nullable=False)
    thickness = db.Column(db.REAL, nullable=False)
    weight = db.Column(db.REAL, nullable=False)
    limitweight = db.Column(db.REAL, nullable=True)
    status = db.Column(db.Integer, nullable=True) # 0 not available, 1 general available, 2 special available
    purpose = db.Column(db.String(100), nullable=True) # for specical purpose, such as SEMIL-2047GC, Nuvo-9650AWP

    def __init__(self, name, abbreviation, height, width, thickness, weight, limitweight, status, purpose):
        self.name = name
        self.abbreviation = abbreviation
        self.height = height
        self.width = width
        self.thickness = thickness
        self.weight = weight    
        self.limitweight = limitweight
        self.status = status
        self.purpose = purpose

    def __repr__(self):
        return '{} by {}'.format(self.name)

#Product add category: NRU, COMPUTER, SEMIL, PB, CARD, GPU, POWERADAPTER, CABLEKIT, DINRAIL, FANKIT, WALLMOUNT, DUMPINGBRACKET
#Product add abbreviation, category, height, width, thickness, weight, inneraccessory,notes
class PnMap(db.Model):
    __tablename__ = 'pnmap'

    id = db.Column(db.Integer, primary_key=True)
    pn = db.Column(db.String(100), nullable=False)
    biosv = db.Column(db.String(100), nullable=False)
    prefix = db.Column(db.String(20), nullable=False)
    net = db.Column(db.Integer, nullable=False)
    poe = db.Column(db.Integer, nullable=False)
    ign = db.Column(db.Integer, nullable=False)
    sop = db.Column(db.String(100), nullable=True)
    unitsinabox = db.Column(db.Integer, nullable=True)
    buildpoints = db.Column(db.Integer, nullable=True)
    customized  = db.Column(db.Integer, nullable=True)
    testonlypoints = db.Column(db.Integer, nullable=True)
    gpu  = db.Column(db.Integer, nullable=True)
    extra  = db.Column(db.REAL, nullable=True)

    abbreviation = db.Column(db.String(32), nullable=True)
    category = db.Column(db.String(16), nullable=True)
    height = db.Column(db.REAL, nullable=True)
    width = db.Column(db.REAL, nullable=True)
    thickness = db.Column(db.REAL, nullable=True)
    weight = db.Column(db.REAL, nullable=True)
    inneraccessory = db.Column(db.String(256), nullable=True)
    notes = db.Column(db.String(256), nullable=True)

    def __init__(self, pn, biosv,prefix, net, poe, ign, sop, unitsinabox, buildpoints, customized, testonlypoints,gpu,extra,abbreviation, category, height, width, thickness, weight, inneraccessory, notes):
        self.pn = pn
        self.biosv = biosv
        self.pn = pn
        self.prefix = prefix
        self.net = net
        self.poe = poe
        self.ign = ign
        self.sop = sop
        self.unitsinabox = unitsinabox
        self.buildpoints = buildpoints
        self.customized = customized
        self.testonlypoints = testonlypoints
        self.gpu = gpu
        self.extra = extra
        self.abbreviation = abbreviation
        self.category = category
        self.height = height
        self.width = width
        self.thickness = thickness
        self.weight = weight
        self.inneraccessory = inneraccessory
        self.notes = notes
        
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
    gpu=db.Column(db.String(100), nullable=True)
    withwifi=db.Column(db.Boolean, nullable=True)
    withcan=db.Column(db.Boolean, nullable=True)
    withfg5g=db.Column(db.Boolean, nullable=True)
    ospreinstalled=db.Column(db.Boolean, nullable=True)
    diskpreinstalled=db.Column(db.Boolean, nullable=True)
    osactivation=db.Column(db.Boolean, nullable=True)

    def __init__(self, wo, customers, pn, csn, cputype, memorysize, gpu, withwifi, withcan,withfg5g, ospreinstalled, diskpreinstalled,\
                disksize, cpuinstall, memoryinstall, gpuinstall,  wifiinstall, caninstall, mezioinstall, fg5ginstall, osinstall, packgo,\
                asid, insid,astime, intime, csid, cstime, tktime, ldtime, status,osactivation):
        self.wo = wo
        self.customers = customers
        self.pn = pn
        self.csn = csn
        self.cputype = cputype
        self.memorysize = memorysize
        self.gpu = gpu
        self.withwifi = withwifi
        self.withcan = withcan
        self.withfg5g = withfg5g
        self.ospreinstalled = ospreinstalled
        self.diskpreinstalled = diskpreinstalled
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
        self.osactivation = osactivation
        
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