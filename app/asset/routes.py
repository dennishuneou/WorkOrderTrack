from flask_login import login_required
from app.asset.forms import AddWorkorderForm, UploadReportForm, ReviewReportForm, ReviewReportFileForm,EditOneComputerForm,ReportSearchForm,QueryForm,ViewReportForm
from app.asset import main
from app.asset.models import WorkOrder, Production
from flask import render_template, flash, request, redirect, url_for
from app import db
#Dennis
#workorder status, unassigned -1, processing 0, waiting for inspection 1 finished 2.
from flask_login import current_user
import datetime
from sqlalchemy import func
from app.auth.forms  import get_userrole, get_usersname, get_useridbyname, get_username
from app.auth.models import User

@main.route('/')
@login_required
def display_workorders():
    role = get_userrole(current_user.id)
    if  datetime.datetime.today().weekday() == 0:
        delta = 3
    else :
        delta = 1
    if role == 0 :
        todoworkorder1 = WorkOrder.query.filter_by(status=-1,asid=-1)
        todoworkorder2 = WorkOrder.query.filter_by(status=-1,asid=current_user.id)
        todoworkorder  = todoworkorder1.union(todoworkorder2)
    else :
        todoworkorder = WorkOrder.query.filter_by(status=-1)  
    todoworkorder = todoworkorder.order_by(WorkOrder.wo)    
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
    cntToday = [0,0,0,0,0]
    cntToday[0] = completed.count()
    #Build, not Pack & Go
    cntToday[1] = cntToday[0] - completed.filter_by(packgo=True).count()
    #OS, installed OS
    cntToday[2] = cntToday[1] - completed.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cntToday[3] = cntToday[1] - completed.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cntToday[4] = completed.filter_by(gpuinstall=True).count()

    #Total
    cnt7day = [0,0,0,0,0]
    cnt7day[0] = completed7day.count()
    #Build, not Pack & Go
    cnt7day[1] = cnt7day[0] - completed7day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt7day[2] = cnt7day[1] - completed7day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt7day[3] = cnt7day[1] - completed7day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt7day[4] = completed7day.filter_by(gpuinstall=True).count()

    #Total
    cnt28day = [0,0,0,0,0]
    cnt28day[0] = completed28day.count()
    #Build, not Pack & Go
    cnt28day[1] = cnt28day[0] - completed28day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt28day[2] = cnt28day[1] - completed28day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt28day[3] = cnt28day[1] - completed28day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt28day[4] = completed28day.filter_by(gpuinstall=True).count()
    
    #Completed  days by user
    tablesearchsummary = []
    users = User.query.all()    
    for user in users :
        if user.role < 3 :
            completedssbyuser=completed7day.filter(WorkOrder.asid == user.id)
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
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
                tablesearchsummary.append(rows)
    searchtable = []                
    for workord in completed7day.order_by(WorkOrder.asid):
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
        searchtable.append(rows)
    return render_template('home.html', todoworkorder= todoworkorder, processing=processing, completed=completed, completedlastwday=completedlastwday,cntToday=cntToday,
                          cnt7day=cnt7day,cnt28day=cnt28day,tablesearchsummary=tablesearchsummary,searchtable=searchtable,userrole=role)

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
                completedss = completedss.order_by(WorkOrder.asid)
                searched = 1
    role = get_userrole(current_user.id)
    if role < 2:
        return redirect(url_for('main.display_workorders'))
    #Search by time, operator name, wo, customer name, pn, csn.
    # user can check the detail of WO and report
    # Name, Customers, WO#, PN, CSN, 
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
                        nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
                        rows.append(nTotal)
                        nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                        rows.append(nInsOS)
                        nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                        rows.append(nInsGPU)
                        nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                        rows.append(nInsModule)
                        nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                        rows.append(nPackgo)
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
            searchtable.append(rows)
    return render_template('query.html', form=form, userrole=role, searched=searched,tablesearchsummary=tablesearchsummary,searchtable=searchtable)

@main.route('/register/report', methods=['GET', 'POST'])
@login_required
def report():
    form = ReportSearchForm()
    searched = 0
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
    cntToday = [0,0,0,0,0]
    cntToday[0] = completed.count()
    #Build, not Pack & Go
    cntToday[1] = cntToday[0] - completed.filter_by(packgo=True).count()
    #OS, installed OS
    cntToday[2] = cntToday[1] - completed.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cntToday[3] = cntToday[1] - completed.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cntToday[4] = completed.filter_by(gpuinstall=True).count()

    #Total
    cnt7day = [0,0,0,0,0]
    cnt7day[0] = completed7day.count()
    #Build, not Pack & Go
    cnt7day[1] = cnt7day[0] - completed7day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt7day[2] = cnt7day[1] - completed7day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt7day[3] = cnt7day[1] - completed7day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt7day[4] = completed7day.filter_by(gpuinstall=True).count()

    #Total
    cnt28day = [0,0,0,0,0]
    cnt28day[0] = completed28day.count()
    #Build, not Pack & Go
    cnt28day[1] = cnt28day[0] - completed28day.filter_by(packgo=True).count()
    #OS, installed OS
    cnt28day[2] = cnt28day[1] - completed28day.filter_by(osinstall='',packgo=False).count()
    #Module, installed module
    cnt28day[3] = cnt28day[1] - completed28day.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False, packgo=False).count()
    #Gpu, Installed GPU
    cnt28day[4] = completed28day.filter_by(gpuinstall=True).count()
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
                nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
                rows.append(nTotal)
                nInsOS = completedssbyuser.filter(WorkOrder.osinstall != '').count()
                rows.append(nInsOS)
                nInsGPU = completedssbyuser.filter(WorkOrder.gpuinstall == True).count()
                rows.append(nInsGPU)
                nInsModule = completedssbyuser.count() - completedssbyuser.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
                rows.append(nInsModule)
                nPackgo= completedssbyuser.filter(WorkOrder.packgo==True).count()
                rows.append(nPackgo)
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
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
              rows.append(nTotal)
              nInsOS = completed1week.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed1week.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed1week.count() - completed1week.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed1week.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
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
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
              rows.append(nTotal)
              nInsOS = completed2weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed2weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed2weeks.count() - completed2weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed2weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
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
              nTotal= nNRU + nPoc + nNuvo5 + nNuvo6 + nNuvo7 + nNuvo8 + nNuvo9 + nNuvoa
              rows.append(nTotal)
              nInsOS = completed4weeks.filter(WorkOrder.osinstall != '').count()
              rows.append(nInsOS)
              nInsGPU = completed4weeks.filter(WorkOrder.gpuinstall == True).count()
              rows.append(nInsGPU)
              nInsModule = completed4weeks.count() - completed4weeks.filter_by(gpuinstall = False,wifiinstall = False, caninstall = False, mezioinstall = False).count()
              rows.append(nInsModule)
              nPackgo= completed4weeks.filter(WorkOrder.packgo==True).count()
              rows.append(nPackgo)
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
        workorder.cpuinstall = form.cpuinstall.data
        workorder.memoryinstall = form.memoryinstall.data
        workorder.gpuinstall = form.gpuinstall.data
        workorder.wifiinstall = form.wifiinstall.data
        workorder.mezioinstall = form.mezioinstall.data
        workorder.caninstall = form.caninstall.data
        workorder.osinstall = form.osinstall.data
        workorder.packgo = form.packgo.data
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

@main.route('/UploadReport/<id>', methods=['GET', 'POST'])
@login_required
def UploadReport(id): 
    workorder = WorkOrder.query.get(id)
    workorder.astime=datetime.datetime.now()
    form = UploadReportForm(obj=workorder)
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
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
        flash('Upload successful')
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
            print(form.action.data)
            if form.action.data == '0' :
                workorder.status = 2
                workorder.insid = current_user.id
            else: 
                workorder.status = 0  
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

@main.route('/register/workorder', methods=['GET', 'POST'])
@login_required
def add_workorder():
    form = AddWorkorderForm()
    role = get_userrole(current_user.id)
    if form.validate_on_submit():
        if form.operator.data == None :
            asidset =-1
        else :
            asidset = form.operator.data.id   
        csn_m=form.csn.data.split('\n')
        for x in csn_m:
            if x.strip() != '' :
                transaction = WorkOrder(wo=form.wo.data, customers=form.customers.data, pn=str(form.pn.data), csn=x.strip(), 
                cpuinstall=form.cpuinstall.data,memoryinstall=form.memoryinstall.data,gpuinstall=form.gpuinstall.data,
                wifiinstall=form.wifiinstall.data,mezioinstall=form.mezioinstall.data,caninstall=form.caninstall.data,
                osinstall=form.osinstall.data,packgo=form.packgo.data,asid=asidset,insid=-1,astime=None,intime=None,tktime=None,csid=current_user.id,cstime=datetime.datetime.now(),status=-1)
                db.session.add(transaction)
        db.session.commit()
        flash('WorkOrder registered successfully')
        return redirect(url_for('main.display_workorders'))
    return render_template('add_workorder.html', form=form, userrole = role)



