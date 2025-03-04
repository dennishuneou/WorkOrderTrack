from flask_login import login_required
from app.asset.forms import AddWorkorderForm, UploadReportForm, ReviewReportForm, ReviewReportFileForm,EditOneComputerForm,ReportSearchForm,QueryForm,ViewReportForm,ReviewOneComputerForm
from app.asset import main
from app.asset.models import WorkOrder, Production, PnMap
from flask import render_template, flash, request, redirect, url_for
from app import db
from app.asset.forms import get_biosversion, get_sopversion
#Dennis
#workorder status, unassigned -1, processing 0, waiting for inspection 1 finished 2.
from flask_login import current_user
import datetime
from sqlalchemy import func
from app.auth.forms  import get_userrole, get_usersname, get_useridbyname, get_username
from app.auth.models import User
import math
from werkzeug.utils import secure_filename
from docx import Document
import os,docx
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSION = {'doc','docx'}
#cputype            null or CPU type 
#memorysize         null or memory size
#disksize           null or disk size
#cpuinstall         True or False, use for score  
#memoryinstall      True or False, use for score  
#gpuinstall         True or False, use for score 
#wifiinstall        True or False, use for score 
#caninstall         True or False, use for score 
#mezioinstall       True or False, use for score 
#fg5ginstall        True or False, use for score 
#osinstall          null or OS name, use for score 
#gpu                True or False or null, use for workorder auto check and score 
#withwifi           True or False or null, use for workorder auto check  
#withcan            True or False or null, use for workorder auto check 
#withfg5g           True or False or null, use for workorder auto check 
#ospreinstalled     True or False or null
#diskpreinstalled   True or False or null
#install cpu,memory or disk\
def testonly(unit): 
    if unit.cpuinstall or unit.memoryinstall or (unit.diskpreinstalled == False) :
        return  False 
    else :    
        return  True
def CalculateUnitBuildScore(unit,basicscoreinfo):
    BuildScore=0
    #basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    # Will not count RMA case        
    if "RNTA" not in unit.wo:
        if unit.packgo != True :
            unitscoreinfo  = basicscoreinfo.filter_by(pn=unit.pn)
            unitbuild    = 6
            unittestonly = 3
            unitgpu      = 0
            unitextra = 0    
            if unitscoreinfo.count() :
                unittestonly = unitscoreinfo[0].testonlypoints
                unitbuild    = unitscoreinfo[0].buildpoints
                unitgpu      = unitscoreinfo[0].gpu
                unitextra    = unitscoreinfo[0].extra  
                maxunitinabox= unitscoreinfo[0].unitsinabox  
                # NRU ? NX ? PCIe ? IGT ? FLYC?
                # NRU-154/156            6/3
                # PCIe-NX154/PCIe-NX156  6/3
            elif "NRU-154" in unit.pn or "NRU-156" in unit.pn\
                    or "IGT-" in unit.pn or "FLYC" in unit.pn\
                    or "PCIe-NX154" in unit.pn or "PCIe-NX156" in unit.pn : 
                unitbuild    = 6
                unittestonly = 3
                # NRU-51V/51V+ 52S/52S+  7/3
            elif "NRU-51V" in unit.pn or "NRU-52S" in unit.pn :
                unitbuild    = 7
                unittestonly = 3
                # NRU-110V/120S/220S     8/4
            elif "NRU-110V" in unit.pn or "NRU-120S" in unit.pn\
                    or "NRU-220S" in unit.pn :
                unitbuild    = 8
                unittestonly = 4
                # NRU-222S/230V/240AWP   8/5
            elif "NRU-222S" in unit.pn or "NRU-230V" in unit.pn\
                    or "NRU-240S" in unit.pn :
                unitbuild    = 8
                unittestonly = 5

            if testonly(unit) :
                BuildScore = BuildScore + unittestonly
                #check disk installation     
                if unit.diskpreinstalled != True and len(unit.memorysize.strip()):
                    BuildScore = BuildScore + 2 
            else :
                BuildScore = BuildScore + unitbuild
            #check OS installation 
            if unit.ospreinstalled != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 1
            #check OS activiation 
            if unit.osactivation != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 0.5
            #check Wifi installation 
            if unit.wifiinstall == True:
                BuildScore = BuildScore + 0.5
            #check can installation 
            if unit.caninstall == True:
                BuildScore = BuildScore + 0.5
            #check mezio installation 
            if unit.mezioinstall == True :
                BuildScore = BuildScore + 0.25
            #check fg5g installation 
            if unit.fg5ginstall == True:
                BuildScore = BuildScore + 1
            #check gpu install
            if unit.gpuinstall == True :
                BuildScore = BuildScore + unitgpu  
            BuildScore = BuildScore + unitextra
    return BuildScore

def CalculateScore(completed,basicscoreinfo):
    BuildScore=0
    PackScore =0
    #basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    completed = completed.order_by(WorkOrder.wo)
    lastwo = ""
    cntinwo= 0.0
    #PCIe card,IGT,FLYC-300
    maxunitinabox = 25 
    #calculate build and test score
    for unit in completed :
        #not count rma CASE
        if unit.wo != lastwo :
            #calculate pack score
            if cntinwo!= 0 :
                PackScore = PackScore + math.ceil( cntinwo / maxunitinabox)*2
                lastwo = unit.wo
                cntinwo= 0.0
                maxunitinabox = 25
        # Will not count RMA case        
        if "RNTA" not in unit.wo:
            #first unit in current wo
            if cntinwo == 0:
               unitscoreinfo  = basicscoreinfo.filter_by(pn=unit.pn)
               unitbuild = 6
               unittestonly = 3
               unitgpu = 0
               unitextra=0
            cntinwo = cntinwo + 1
            if unit.packgo == True:
               continue
            if cntinwo == 1:
               if unitscoreinfo.count() :
                 unittestonly = unitscoreinfo[0].testonlypoints
                 unitbuild    = unitscoreinfo[0].buildpoints
                 unitgpu      = unitscoreinfo[0].gpu
                 unitextra    = unitscoreinfo[0].extra 
                 maxunitinabox= unitscoreinfo[0].unitsinabox  
                # NRU ? NX ? PCIe ? IGT ? FLYC?
                # NRU-154/156            6/3
                # PCIe-NX154/PCIe-NX156  6/3
               elif "NRU-154" in unit.pn or "NRU-156" in unit.pn\
                   or "IGT-" in unit.pn or "FLYC" in unit.pn\
                   or "PCIe-NX154" in unit.pn or "PCIe-NX156" in unit.pn : 
                 unitbuild    = 6
                 unittestonly = 3
                 maxunitinabox= 4 
                # NRU-51V/51V+ 52S/52S+  7/3
               elif "NRU-51V" in unit.pn or "NRU-52S" in unit.pn :
                 unitbuild    = 7
                 unittestonly = 3
                 maxunitinabox= 4 
                # NRU-110V/120S/220S     8/4
               elif "NRU-110V" in unit.pn or "NRU-120S" in unit.pn\
                    or "NRU-220S" in unit.pn :
                 unitbuild    = 8
                 unittestonly = 4
                 maxunitinabox= 4 
                # NRU-222S/230V/240AWP   8/5
               elif "NRU-222S" in unit.pn or "NRU-230V" in unit.pn\
                    or "NRU-240S" in unit.pn :
                 unitbuild    = 8
                 unittestonly = 5
                 maxunitinabox= 4 
            if testonly(unit) :
                BuildScore = BuildScore + unittestonly
                #check disk installation     
                if unit.diskpreinstalled != True and len(unit.memorysize.strip()):
                    BuildScore = BuildScore + 2 
            else :
                BuildScore = BuildScore + unitbuild
            #check OS installation 
            if unit.ospreinstalled != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 1
            #check OS activiation 
            if unit.osactivation != True and len(unit.osinstall.strip()):
                BuildScore = BuildScore + 0.5
            #check Wifi installation 
            if unit.wifiinstall == True:
                BuildScore = BuildScore + 0.5
            #check can installation 
            if unit.caninstall == True:
                BuildScore = BuildScore + 0.5
            #check mezio installation 
            if unit.mezioinstall == True :
                BuildScore = BuildScore + 0.25
            #check fg5g installation 
            if unit.fg5ginstall == True:
                BuildScore = BuildScore + 1
            #check gpu install
            if unit.gpuinstall == True :
                BuildScore = BuildScore + unitgpu  
            BuildScore = BuildScore + unitextra
    #last wororder            
    if cntinwo!= 0 :
        PackScore = PackScore + math.ceil( cntinwo / maxunitinabox)*2
    #calculate pack score by workorder
    return (BuildScore+PackScore)

@main.route('/takemore', methods=['GET', 'POST'])
@login_required
def takemore():
    print("take more")
    x = request.json
    y = x.get("message")
    z = y.split()
    for sid in z:
        print(sid)
        workorder = WorkOrder.query.get(sid)
        workorder.status=0
        workorder.asid=current_user.id
        workorder.tktime=datetime.datetime.now()
        db.session.commit()
    return redirect(url_for('main.display_workorders'))
    
@main.route('/uploadmore', methods=['GET', 'POST'])
@login_required
def uploadmore():
    print("upload more")
    x = request.json
    y = x.get("message")
    z = y.split()
    for sid in z:
        print(sid)
        workorder = WorkOrder.query.get(sid)
        if(workorder.packgo == True):
            workorder.astime=datetime.datetime.now()
            workorder.status = 1
            transaction = Production(wo=workorder.wo, pn=workorder.pn, csn=workorder.csn, msn="N/A", cpu="N/A",mem1="", mem2="", mem3="", mem4="", gpu1="", gpu2="", 
            sata1="", sata2="",sata3="", sata4="", m21="", m22="", wifi="", fg5g="",can="",other="",note="",report="")
            existproduct = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn)
            if existproduct.count() :
                db.session.delete(existproduct[0])
            db.session.add(transaction)
            db.session.commit()
    return redirect(url_for('main.display_workorders'))

@main.route('/inspectmore', methods=['GET', 'POST'])
@login_required
def inspectmore():
    print("inspect more")
    x = request.json
    y = x.get("message")
    z = y.split()
    for sid in z:
        print(sid)
        workorder = WorkOrder.query.get(sid)
        if(workorder.packgo == True):
            workorder.intime=datetime.datetime.now()
            if workorder.status == 1:
                workorder.status = 2
                workorder.insid = current_user.id
            db.session.commit()
    return redirect(url_for('main.display_workorders'))    

@main.route('/')
@login_required
def display_workorders():
    role = get_userrole(current_user.id)
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    if  datetime.datetime.today().weekday() == 0:
        delta = 3
    else :
        delta = 1
    if role == 0 :
        todoworkorder1 = WorkOrder.query.filter_by(status=-1,asid=-1)
        todoworkorder2 = WorkOrder.query.filter_by(status=-1,asid=current_user.id)
        todoworkorder  = todoworkorder1.union(todoworkorder2)
        pendingworkorder1 = WorkOrder.query.filter_by(status=-2,asid=-1)
        pendingworkorder2 = WorkOrder.query.filter_by(status=-2,asid=current_user.id)
        pendingworkorder  = pendingworkorder1.union(todoworkorder2)
    else :
        todoworkorder = WorkOrder.query.filter_by(status=-1)  
        pendingworkorder = WorkOrder.query.filter_by(status=-2)  
    todoworkorder = todoworkorder.order_by(WorkOrder.wo)    
    pendingworkorder = pendingworkorder.order_by(WorkOrder.wo)    
    if role == 0 :
        query1 = WorkOrder.query.filter_by(asid=current_user.id, status=0)
        query2 =  WorkOrder.query.filter_by(asid=current_user.id, status=1)
    else :
        query1 = WorkOrder.query.filter_by(status=0)
        query2 =  WorkOrder.query.filter_by(status=1)
    processing = query1.union(query2)
    processing = processing.order_by(WorkOrder.wo) 
    if role == 0 :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
        completedlastwday = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == (func.DATE(datetime.datetime.today())-delta),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
        completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
        completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.asid==current_user.id,WorkOrder.status == 2)
    else :
        completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.status == 2)
        completedlastwday = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == (func.DATE(datetime.datetime.today())-delta),WorkOrder.status == 2)
        completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2)
        completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2)
    completed = completed.order_by(WorkOrder.wo)
    completedlastwday = completedlastwday.order_by(WorkOrder.wo)
    #Total
    cntToday = [0,0,0,0,0,0]
    cntToday[0] = completed.count()
    #Build, not Pack & Go
    cntToday[1] = cntToday[0] - completed.filter_by(packgo=True).count()
    #OS, installed OS
    cntToday[2] = cntToday[1] - completed.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cntToday[3] = cntToday[1] - completed.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cntToday[4] = completed.filter_by(gpuinstall=True).count()
    #Score
    cntToday[5] = CalculateScore(completed.order_by(WorkOrder.wo),basicscoreinfo)
    #Total
    cnt7day = [0,0,0,0,0,0]
    cnt7day[0] = completed7day.count()
    #Build, not Pack & Go
    cnt7day[1] = cnt7day[0] - completed7day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt7day[2] = cnt7day[1] - completed7day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt7day[3] = cnt7day[1] - completed7day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt7day[4] = completed7day.filter_by(gpuinstall=True).count()
    #Score
    cnt7day[5] = CalculateScore(completed7day.order_by(WorkOrder.wo),basicscoreinfo)

    #Total
    cnt28day = [0,0,0,0,0,0]
    cnt28day[0] = completed28day.count()
    #Build, not Pack & Go
    cnt28day[1] = cnt28day[0] - completed28day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt28day[2] = cnt28day[1] - completed28day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt28day[3] = cnt28day[1] - completed28day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt28day[4] = completed28day.filter_by(gpuinstall=True).count()
    cnt28day[5] = CalculateScore(completed28day.order_by(WorkOrder.wo),basicscoreinfo)

    #Completed last weekday by user
    tablesearchsummary1day = []
    users = User.query.all()    
    for user in users :
        if user.role < 3 :
            completedssbyuser=completedlastwday.filter(WorkOrder.asid == user.id)
            if completedssbyuser.count() :
                #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, SEMIL, Pack&Go
                rows = []
                rows.append(user.user_name)
                nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNRU)
                nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                rows.append(nPoc)
                nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo5)
                nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo6)
                nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo7)
                nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo8)
                nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo9)
                nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvoa)
                nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                rows.append(nSemil)
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
                nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                rows.append(nScore)
                tablesearchsummary1day.append(rows)
    #Completed 7 days by user
    tablesearchsummary = []
    users = User.query.all()    
    for user in users :
        if user.role < 3 :
            completedssbyuser=completed7day.filter(WorkOrder.asid == user.id)
            if completedssbyuser.count() :
                #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, SEMIL, Pack&Go
                rows = []
                rows.append(user.user_name)
                nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNRU)
                nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                rows.append(nPoc)
                nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo5)
                nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo6)
                nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo7)
                nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo8)
                nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo9)
                nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvoa)
                nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                rows.append(nSemil)
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
                nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                rows.append(nScore)
                tablesearchsummary.append(rows)
    completedlastwday = completedlastwday.filter(WorkOrder.packgo!=True).order_by(WorkOrder.asid)             
   
    searchtable = []  
    seq = 0;
    for workord in completed7day.filter(WorkOrder.packgo!=True).order_by(WorkOrder.asid):
        rows = []
        seq = seq + 1
        rows.append(seq)
        rows.append(workord.wo)
        rows.append(workord.customers)
        rows.append(workord.pn)
        rows.append(workord.csn)
        rows.append(workord.cstime.strftime("%m/%d %H:%M"))
        rows.append(workord.tktime.strftime("%m/%d %H:%M"))
        rows.append(get_username(workord.asid))
        rows.append(workord.astime.strftime("%m/%d %H:%M"))
        rows.append(get_username(workord.insid))
        rows.append(workord.intime.strftime("%m/%d %H:%M"))
        rows.append(CalculateUnitBuildScore(workord,basicscoreinfo))
        searchtable.append(rows)
    return render_template('home.html', todoworkorder= todoworkorder, pendingworkorder= pendingworkorder, processing=processing, completed=completed, completedlastwday=completedlastwday,cntToday=cntToday,
                          cnt7day=cnt7day,cnt28day=cnt28day,tablesearchsummary=tablesearchsummary,tablesearchsummary1day=tablesearchsummary1day,searchtable=searchtable,userrole=role)

@main.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    form = QueryForm()
    searched = 0
    if request.method == "POST":
        #Prepare the search results between start date and end date
        if form.enddate.data != None and form.startdate.data != None:
            if form.enddate.data >= form.startdate.data :
                completedss = WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(form.startdate.data ),WorkOrder.status == 2)
                completedss = completedss.filter((func.DATE(WorkOrder.intime)) <= (func.DATE(form.enddate.data )))
                print(form.packgo.data)
                if(form.packgo.data != True) :
                    completedss = completedss.filter(WorkOrder.packgo!=True)
                completedss = completedss.order_by(WorkOrder.asid)
                searched = 1
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    #Search by time, operator name, wo, customer name, pn, csn.
    # user can check the detail of WO and report
    # Name, Customers, WO#, PN, CSN, 
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    searchtable = []
    tablesearchsummary = []
    if searched == 1 :
        if form.operator.data != None :
            asid = get_useridbyname(form.operator.data.user_name)
            completedss = completedss.filter(WorkOrder.asid == asid)
            print(1)
        if form.wo.data != '':
            wo = form.wo.data
            completedss = completedss.filter(WorkOrder.wo == wo)
            print(2)
        if form.pn.data != '' :
            pn = form.pn.data
            completedss = completedss.filter(WorkOrder.pn.contains(pn))
            print(3)
        if form.csn.data != '' :
            csn = form.csn.data
            completedss = completedss.filter(WorkOrder.csn.contains(csn))
            print(4)
        if form.customers.data != '' :
            customer = form.customers.data
            completedss = completedss.filter(WorkOrder.customers.contains(customer))
        users = User.query.all()    
        for user in users :
            if user.role < 3 :
                if searched == 1:
                    completedssbyuser=completedss.filter(WorkOrder.asid == user.id)
                    if completedssbyuser.count() :
                    #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
                        rows = []
                        rows.append(user.user_name)
                        nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNRU)
                        nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nPoc)
                        nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo5)
                        nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo6)
                        nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo7)
                        nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo8)
                        nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvo9)
                        nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nNuvoa)
                        nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                        rows.append(nSemil)
                        nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
                        rows.append(nTotal)
                        nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                        rows.append(nInsOS)
                        nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                        rows.append(nInsGPU)
                        nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                        rows.append(nInsModule)
                        nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                        rows.append(nPackgo)
                        nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                        rows.append(nScore)
                        tablesearchsummary.append(rows)
        for workord in completedss :
            rows = []
            rows.append(workord.id)
            rows.append(workord.wo)
            rows.append(workord.customers)
            rows.append(workord.pn)
            rows.append(workord.csn)
            rows.append(workord.cstime.strftime("%m/%d %H:%M"))
            rows.append(workord.tktime.strftime("%m/%d %H:%M"))
            rows.append(get_username(workord.asid))
            rows.append(workord.astime.strftime("%m/%d %H:%M"))
            rows.append(get_username(workord.insid))
            rows.append(workord.intime.strftime("%m/%d %H:%M"))
            rows.append(CalculateUnitBuildScore(workord,basicscoreinfo))
            searchtable.append(rows)
    return render_template('query.html', form=form, userrole=role, searched=searched,tablesearchsummary=tablesearchsummary,searchtable=searchtable)

@main.route('/register/report', methods=['GET', 'POST'])
@login_required
def report():
    form = ReportSearchForm()
    searched = 0
    basicscoreinfo = PnMap.query.filter(PnMap.id!=0)
    if request.method == "POST":
        #Prepare the search results between start date and end date
        if form.enddate.data != None and form.startdate.data != None:
            if form.enddate.data >= form.startdate.data :
                completedss = WorkOrder.query.filter(func.DATE(WorkOrder.intime) >= func.DATE(form.startdate.data ),WorkOrder.status == 2)
                completedss = completedss.filter((func.DATE(WorkOrder.intime)) <= (func.DATE(form.enddate.data )))
                searched = 1
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))

    completed = WorkOrder.query.filter(func.DATE(WorkOrder.intime) == func.DATE(datetime.datetime.today()),WorkOrder.status == 2)
    completed7day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2)
    completed28day = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2)
    #Total
    cntToday = [0,0,0,0,0,0]
    cntToday[0] = completed.count()
    #Build, not Pack & Go
    cntToday[1] = cntToday[0] - completed.filter_by(packgo=True).count()
    #OS, installed OS
    cntToday[2] = cntToday[1] - completed.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cntToday[3] = cntToday[1] - completed.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cntToday[4] = completed.filter_by(gpuinstall=True).count()
    #Score
    cntToday[5] = CalculateScore(completed.order_by(WorkOrder.wo),basicscoreinfo)

    #Total
    cnt7day = [0,0,0,0,0,0]
    cnt7day[0] = completed7day.count()
    #Build, not Pack & Go
    cnt7day[1] = cnt7day[0] - completed7day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt7day[2] = cnt7day[1] - completed7day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt7day[3] = cnt7day[1] - completed7day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt7day[4] = completed7day.filter_by(gpuinstall=True).count()
    #Score
    cnt7day[5] = CalculateScore(completed7day.order_by(WorkOrder.wo),basicscoreinfo)

    #Total
    cnt28day = [0,0,0,0,0,0]
    cnt28day[0] = completed28day.count()
    #Build, not Pack & Go
    cnt28day[1] = cnt28day[0] - completed28day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt28day[2] = cnt28day[1] - completed28day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt28day[3] = cnt28day[1] - completed28day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt28day[4] = completed28day.filter_by(gpuinstall=True).count()
    #Score
    cnt28day[5] = CalculateScore(completed28day.order_by(WorkOrder.wo),basicscoreinfo)

    #Last 2 wwek, 4 week performance
    # Operator name,  POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
    users = User.query.all()
    
    table1week  = []
    table2weeks = []
    table4weeks = []
    tablesearch = []
    for user in users :
        if user.role < 3 :
           completed1week  = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-7),WorkOrder.status == 2, WorkOrder.asid == user.id)
           completed2weeks = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-14),WorkOrder.status == 2, WorkOrder.asid == user.id)
           completed4weeks = WorkOrder.query.filter((func.DATE(WorkOrder.intime)) >= (func.DATE(datetime.datetime.today())-28),WorkOrder.status == 2, WorkOrder.asid == user.id)
           if searched == 1:
              completedssbyuser=completedss.filter(WorkOrder.asid == user.id)
              if completedssbyuser.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
                rows = []
                rows.append(user.user_name)
                nNRU = completedssbyuser.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNRU)
                nPoc = completedssbyuser.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completedssbyuser.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
                rows.append(nPoc)
                nNuvo5= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo5)
                nNuvo6= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo6)
                nNuvo7= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo7)
                nNuvo8= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo8)
                nNuvo9= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvo9)
                nNuvoa= completedssbyuser.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
                rows.append(nNuvoa)
                nSemil= completedssbyuser.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
                rows.append(nSemil)
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
                nScore = CalculateScore(completedssbyuser.order_by(WorkOrder.wo),basicscoreinfo)
                rows.append(nScore)
                tablesearch.append(rows)
           if completed1week.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed1week.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed1week.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed1week.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed1week.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5)
              nNuvo6= completed1week.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo6)
              nNuvo7= completed1week.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo7)
              nNuvo8= completed1week.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed1week.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed1week.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nSemil= completed1week.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
              rows.append(nTotal)
              nInsOS = completed1week.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed1week.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed1week.count() - completed1week.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed1week.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed1week.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table1week.append(rows)

           if completed2weeks.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed2weeks.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed2weeks.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed2weeks.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5)
              nNuvo6= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo6)
              nNuvo7= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo7)
              nNuvo8= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed2weeks.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nSemil= completed2weeks.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
              rows.append(nTotal)
              nInsOS = completed2weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed2weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed2weeks.count() - completed2weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed2weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed2weeks.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table2weeks.append(rows)

           if completed4weeks.count() :
              #calculate POC, Nuvo-5000, Nuvo-6000, Nuvo-7000, Nuvo-8000,Nuvo-9000, Muvo-10000, Pack&Go
              rows = []
              rows.append(user.user_name)
              nNRU = completed4weeks.filter(WorkOrder.pn.contains("NRU")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNRU)
              nPoc = completed4weeks.filter(WorkOrder.pn.contains("POC")).filter(WorkOrder.packgo!=True).count()+completed4weeks.filter(WorkOrder.pn.contains("IGT")).filter(WorkOrder.packgo!=True).count()
              rows.append(nPoc)
              nNuvo5= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-5")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo5)
              nNuvo6= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-6")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo6)
              nNuvo7= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-7")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo7)
              nNuvo8= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-8")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo8)
              nNuvo9= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-9")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvo9)
              nNuvoa= completed4weeks.filter(WorkOrder.pn.contains("Nuvo-10")).filter(WorkOrder.packgo!=True).count()
              rows.append(nNuvoa)
              nSemil= completed4weeks.filter(WorkOrder.pn.contains("SEMIL")).filter(WorkOrder.packgo!=True).count()
              rows.append(nSemil)
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa + nSemil
              rows.append(nTotal)
              nInsOS = completed4weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed4weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed4weeks.count() - completed4weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed4weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
              nScore = CalculateScore(completed4weeks.order_by(WorkOrder.wo),basicscoreinfo)
              rows.append(nScore)
              table4weeks.append(rows)

    return render_template('report.html', cntToday=cntToday,cnt7day=cnt7day,cnt28day=cnt28day,userrole=role,table1week=table1week,table2weeks=table2weeks,table4weeks=table4weeks,form=form,tablesearch=tablesearch,searched=searched)
    
@main.route('/TakeOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def TakeOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=0
    workorder.asid=current_user.id
    workorder.tktime=datetime.datetime.now()
    db.session.commit()
    
    flash('TakeOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/DeleteOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def DeleteOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    db.session.delete(workorder)
    products = Production.query.filter_by(wo = workorder.wo, csn =workorder.csn)
    if products.count() :
        db.session.delete(products[0])
    db.session.commit()
    flash('DeleteOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/EditOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def EditOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    form = EditOneComputerForm(obj=workorder)
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        print(form.cpuinstall.data)
        workorder.wo=form.wo.data
        workorder.customers=form.customers.data
        workorder.pn=str(form.pn.data)
        workorder.csn=form.csn.data.strip()
        workorder.cputype = form.cputype.data
        workorder.memorysize = form.memorysize.data
        workorder.disksize = form.disksize.data
        workorder.cpuinstall = form.cpuinstall.data
        workorder.memoryinstall = form.memoryinstall.data
        workorder.gpuinstall = form.gpuinstall.data
        workorder.wifiinstall = form.wifiinstall.data
        workorder.mezioinstall = form.mezioinstall.data
        workorder.caninstall = form.caninstall.data
        workorder.fg5ginstall = form.fg5ginstall.data
        workorder.osinstall = form.osinstall.data
        workorder.packgo = form.packgo.data
        workorder.ldtime = form.ldtime.data
        workorder.gpu=form.gpu.data
        workorder.withwifi=form.withwifi.data
        workorder.withcan=form.withcan.data
        workorder.withfg5g=form.withfg5g.data
        workorder.ospreinstalled=form.ospreinstalled.data
        workorder.osactivation=form.osactivation.data
        workorder.diskpreinstalled=form.diskpreinstalled.data
        if form.operator.data == None :
            asidset =-1
        else :
            asidset = form.operator.data.id
        workorder.asid = asidset    
        workorder.csid = current_user.id
        workorder.cstime=datetime.datetime.now()
        db.session.commit()
        flash('Update successful')
        return redirect(url_for('main.display_workorders'))
    return render_template('edit_OneComputer.html', form=form, id=id, userrole=role) 

@main.route('/DeactiveOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def DeactiveOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-2
    db.session.commit()
    
    flash('DeactiveOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/RestoreOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def RestoreOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-1
    db.session.commit()
    
    flash('RestoreOneComputer successfully')
    return redirect(url_for('main.display_workorders'))

@main.route('/UploadReport/<id>', methods=['GET', 'POST'])
@login_required
def UploadReport(id): 
    workorder = WorkOrder.query.get(id)
    workorder.astime=datetime.datetime.now()
    form = UploadReportForm(obj=workorder)
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        if(workorder.status != 0):
            fstr = "Please take workorder before upload report!"
            flash(fstr)
            return render_template('uploadreport.html', form=form, id=id,userrole = role)
        else :     
            workorder.status = 1
            transaction = Production(wo=form.wo.data, pn=form.pn.data, csn=form.csn.data, msn=form.msn.data, cpu=form.cpu.data, 
            mem1=form.mem1.data, mem2=form.mem2.data, mem3=form.mem3.data, mem4=form.mem4.data, gpu1=form.gpu1.data, gpu2=form.gpu2.data, sata1=form.sata1.data, sata2=form.sata2.data,
            sata3=form.sata3.data, sata4=form.sata4.data, m21=form.m21.data, m22=form.m22.data, wifi=form.wifi.data, fg5g=form.fg5g.data,
            can=form.can.data,other=form.other.data,note=form.note.data,report=form.report.data)
            existproduct = Production.query.filter_by(wo=form.wo.data,csn=form.csn.data.strip())
            if existproduct.count() :
                db.session.delete(existproduct[0])
            db.session.add(transaction)
            db.session.commit()
            fstr = "Upload successful! "
            if workorder.cpuinstall == False and ("Nuvo" in workorder.pn or "SEMIL" in workorder.pn):
                fstr += "PLEASE uninstall CPU. "
            if workorder.memoryinstall == False and ("Nuvo" in workorder.pn or "POC" in workorder.pn or "SEMIL" in workorder.pn) :    
                fstr += "PLEASE uninstall Memory."
            if "WARNING" in form.note.data :
                fstr += form.note.data     
            flash(fstr)
            return redirect(url_for('main.display_workorders'))
    return render_template('uploadreport.html', form=form, id=id,userrole = role)

@main.route('/ReviewReport/<id>', methods=['GET', 'POST'])
@login_required
def ReviewReport(id):
        workorder = WorkOrder.query.get(id)
        products = Production.query.filter_by(wo=workorder.wo,csn=workorder.csn.strip())
        form = ReviewReportForm(obj=workorder)
        role = get_userrole(current_user.id)
        if products.count()>0 :
            product = products[0]
            if request.method == "GET":	
            	form.cpu.data = product.cpu
            	form.msn.data = product.msn
            	form.report.data = product.report   
            	form.mem1.data = product.mem1
            	form.mem2.data = product.mem2
            	form.mem3.data = product.mem3
            	form.mem4.data = product.mem4
            	form.gpu1.data = product.gpu1
            	form.gpu2.data = product.gpu2
            	form.sata1.data= product.sata1
            	form.sata2.data= product.sata2
            	form.sata3.data= product.sata3
            	form.sata4.data= product.sata4
            	form.m21.data= product.m21
            	form.m22.data= product.m22
            	form.wifi.data=product.wifi
            	form.fg5g.data=product.fg5g
            	form.can.data =product.can
            	form.other.data=product.other
            	form.note.data=product.note
        workorder.intime=datetime.datetime.now()
        if form.validate_on_submit():
            if form.action.data == '0' :
                workorder.status = 2
                workorder.insid = current_user.id
            else: 
                workorder.status = 0  
            product.note=form.note.data # update notes
            product.cpu=form.cpu.data # update CPU
            product.m21=form.m21.data
            product.m22=form.m22.data
            db.session.commit()
            if(form.action.data=='0') :
               flash('Approved')
            else :
               flash('Denied')
            return redirect(url_for('main.display_workorders'))
        return render_template('reviewreport.html', form=form, id=id, userrole = role)

@main.route('/ViewReport/<wo>/<csn>', methods=['GET', 'POST'])
@login_required
def ViewReport(wo,csn):
        products = Production.query.filter_by(wo=wo,csn=csn)
        form = ViewReportForm(obj=products[0])
        role = get_userrole(current_user.id)
        return render_template('viewreport.html', form=form, userrole = role)


@main.route('/ReturnOneComputer/<id>', methods=['GET', 'POST'])
@login_required
def ReturnOneComputer(id): 
    workorder = WorkOrder.query.get(id)
    workorder.status=-1
    workorder.asid=-1;
    workorder.astime=None
    db.session.commit()
    
    flash('ReturnOneComputer successfully')
    return redirect(url_for('main.display_workorders'))    

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSION 

def get_header_tables(doc):
    header_tables = []
    for section in doc.sections:
        header = section.header
        for element in header._element.xpath('//w:tbl'):
            table = docx.table.Table(element, header)
            header_tables.append(table)
    return header_tables

@main.route('/register/workorder', methods=['GET', 'POST'])
@login_required
def add_workorder():
    form = AddWorkorderForm()
    role = get_userrole(current_user.id)
    if request.method == 'POST' :
        if 'readdocfile' in request.form :
           if request.form['readdocfile'] == 'Upload' and 'file' in  request.files:
                file = request.files['file'] 
                print(file.filename)
                if file.filename == '' :
                   return 'No selected file'
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER,filename)
                    file.save(filepath)
                    #Extract text fome the .docx file
                    doc = Document(filepath)
                    wocontent = []
                    linecnt = 0
                    colcnt = 0
                    foundPN = False
                    foundWO = False  
                    searchend = False 
                    customer = []
                    #Get customer information
                    header_tables = get_header_tables(doc)
                    for table in header_tables :
                            if not searchend :
                                for row in table.rows :
                                    colcnt = 0
                                    linecontent = []
                                    if not searchend :
                                        for cell in row.cells:
                                            if not foundWO :
                                                if colcnt == 0 and 'Customer' in cell.text:
                                                #find 
                                                    foundWO = True
                                                    linecontent.append(cell.text)
                                            else :       
                                                linecontent.append(cell.text)
                                            colcnt = colcnt + 1   
                                        customer.append(linecontent)
                                searchend =  foundWO
                    for row in customer :
                        if 'NTA Order ID' in row:
                            form.wo.data = row[1]
                        else :
                            for cell in row :
                                if 'Customer' == cell.strip():    
                                    form.customers.data = row[1]
                    searchend = False                                          
                    #Search content
                    for table in doc.tables :
                            if not searchend :
                                for row in table.rows :
                                    colcnt = 0
                                    linecontent = []
                                    if not searchend :
                                        for cell in row.cells:
                                            if not foundPN :
                                                if colcnt == 0 and 'Product Number' in cell.text:
                                                #find 
                                                    foundPN = True
                                                    linecontent.append(cell.text)
                                            else :       
                                                linecontent.append(cell.text)
                                            if 'End of Part' in cell.text :
                                                searchend = True
                                                break; 
                                            colcnt = colcnt + 1   
                                        wocontent.append(linecontent)
                                #print(wocontent)
                    #['Product Number', 'QTY', 'S/N', 'Notes', 'Check']
                    form.pn.data = wocontent[1][0]
                    count = int(wocontent[1][1])
                    form.csn.data = wocontent[1][2]
                    form.disksize.data=''
                    for row in wocontent :
                        if  'DDR3' in row[0] or 'DDR4' in row[0] or 'DDR5' in row[0]:
                            ddrcnt = int(row[1]) / count
                            ddrstr = row[0].split('-')
                            for ddrsize in ddrstr :
                                if 'GB' in ddrsize :
                                    form.memorysize.data = ddrsize + 'x' + str(int(ddrcnt))
                            if 'installed' not in row[3] :
                                form.memoryinstall.data = True
                            else :
                                form.memoryinstall.data = False
                        elif 'SSD' in row[0].upper():
                            ssdcnt = int(row[1]) / count
                            ssdstr = row[0].split('-')
                            for ssdsize in ssdstr :
                                if 'GB' in ssdsize.upper() or 'TB' in ssdsize.upper():
                                    if 'PCIE' in row[0].upper():
                                        form.disksize.data = form.disksize.data + 'NVME' + ssdsize + 'x' + str(int(ssdcnt)) + '  '
                                    else :
                                        form.disksize.data = form.disksize.data + 'SSD' + ssdsize + 'x' + str(int(ssdcnt)) + '  '    
                            if 'installed' not in row[3] :
                                form.diskpreinstalled.data = False
                            else :
                                form.diskpreinstalled.data = True
                        elif 'RTX' in row[0].upper() or 'GTX' in row[0].upper() :
                            gpucnt = int(row[1]) / count
                            gpustr = row[0].split('-')
                            for gpusize in gpustr :
                                if 'RTX' in gpusize or 'GTX' in gpusize :
                                    form.gpu.data = gpusize + 'x' + str(int(gpucnt))
                            if 'installed' not in row[3] :
                                form.gpuinstall.data = True
                            else :
                                form.gpuinstall.data = False
                        elif  'CAN' in row[0].upper():
                            form.withcan.data = True
                            if 'installed' not in row[3] :
                                form.caninstall.data = True
                        elif 'WIFI' in row[0].upper():
                            form.withwifi.data = True
                            if 'installed' not in row[3] :
                                form.wifiinstall.data = True
                        elif 'MEZIO' in row[0].upper():   
                            if 'installed' not in row[3] :
                                form.mezioinstall.data = True
                        elif  'LTE-7455' in row[0] :   
                            form.withfg5g.data = True
                            if 'installed' not in row[3] :
                                form.fg5ginstall.data = True
                        elif 'WIN' in row[0].upper() or 'UBUNTU' in row[0].upper() or 'JP' in row[0].upper() \
                                or 'JETSON' in row[0].upper():
                            form.osinstall.data = row[0]
                            if 'installed' not in row[3] :
                                form.osinstall.data = row[0]
                            else :
                                form.ospreinstalled.data = True   
                        elif 'I7-' in row[0].upper() or 'I9-' in row[0].upper() or 'E22' in row[0].upper() \
                             or 'I3-' in row[0].upper() or 'I5-' in row[0].upper()  \
                             or 'AGX' in row[0].upper() or 'ORIN' in row[0].upper() :
                            form.cputype.data = row[0]
                            if 'installed' not in row[3] :
                                form.cpuinstall.data = True
                            else :
                                form.cpuinstall.data = False
                    os.remove(filepath)
        elif form.validate_on_submit():
            if form.operator.data == None :
                asidset =-1
            else :
                asidset = form.operator.data.id   
            csn_m=form.csn.data.split('\n')
            for x in csn_m:
                if x.strip() != '' :
                    transaction = WorkOrder(wo=form.wo.data, customers=form.customers.data, pn=str(form.pn.data), csn=x.strip(), 
                    cputype=form.cputype.data,memorysize=form.memorysize.data,disksize=form.disksize.data,cpuinstall=form.cpuinstall.data,memoryinstall=form.memoryinstall.data,gpuinstall=form.gpuinstall.data,
                    wifiinstall=form.wifiinstall.data,mezioinstall=form.mezioinstall.data,caninstall=form.caninstall.data,fg5ginstall=form.fg5ginstall.data,
                    gpu=form.gpu.data,withwifi=form.withwifi.data,withcan=form.withcan.data,withfg5g=form.withfg5g.data,ospreinstalled=form.ospreinstalled.data,
                    osactivation=form.osactivation.data,diskpreinstalled=form.diskpreinstalled.data,
                    osinstall=form.osinstall.data,packgo=form.packgo.data,asid=asidset,insid=-1,astime=None,intime=None,tktime=None,csid=current_user.id,cstime=datetime.datetime.now(),ldtime=form.ldtime.data,status=-1)
                    db.session.add(transaction)
            db.session.commit()
            flash('WorkOrder registered successfully')
            return redirect(url_for('main.display_workorders'))
    productlist = PnMap.query.with_entities(PnMap.pn).all()
    products = []
    for x in productlist :
        pns = f"{x}"
        pns = pns.replace("('","")
        pns = pns.replace("',)","")
        print(pns)
        products.append(pns)
    return render_template('add_workorder.html', form=form, userrole = role,products=products)

@main.route('/CheckWorkOrder/<id>', methods=['GET', 'POST'])
@login_required
def CheckWorkOrder(id): 
    workorder = WorkOrder.query.get(id)
    form = ReviewOneComputerForm(obj=workorder)
    biosver = get_biosversion(workorder.pn)
    sopver  = get_sopversion(workorder.pn)
    form.biosver.data = biosver
    form.sopver.data = sopver
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        return redirect(url_for('main.display_workorders'))
    return render_template('CheckWorkOrder.html', form=form, id=id, userrole = role, biosver=biosver) 
def getcustomizedstr(item):
    customizedstr ="" 
    if item & 1 :
       customizedstr = customizedstr + " BIOS"
    if item & 2 :
       customizedstr = customizedstr + " SOP"     
    if item & 4 :
       customizedstr = customizedstr + " Chassis"   
    return customizedstr
@main.route('/customized', methods=['GET', 'POST'])
@login_required
def customized(): 
    customizedmodels = PnMap.query.filter(PnMap.customized!=0)
    role = get_userrole(current_user.id)
    return render_template('Customized.html', customizedmodels=customizedmodels, userrole = role,getcustomizedstr=getcustomizedstr) 
