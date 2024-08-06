from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, SelectField, ValidationError,BooleanField, DateField
from wtforms.validators import DataRequired, Length, InputRequired
from wtforms.fields.html5 import DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import TextArea
from app.asset.models import WorkOrder, Production, PnMap
from app.auth.forms  import get_userrole,get_usersname,get_operateusersname
from datetime import datetime

def get_biosversion(psn):
    biosv = PnMap.query.filter_by(pn=psn)
    if biosv.count() :
        return biosv[0].biosv
    else :
        return ''
def get_sopversion(psn):
    sopv = PnMap.query.filter_by(pn=psn)
    if sopv.count() :
        return sopv[0].sop
    else :
        return "Not found"        
def wocsn_exists(form, field):
    csn_m=form.csn.data.split('\n')
    duplicated=0
    csntoolong=0
    for x in csn_m:
        if x.strip() != '' :
            if len(x.strip()) < 100 :
               if WorkOrder.query.filter_by(wo=form.wo.data,csn=x.strip()).count() :
                  duplicated=1
            else :
                csntoolong=1
    if duplicated:
        raise ValidationError('Same WO# with same CSN#')
    if csntoolong:
        raise ValidationError('CSN# longer than 100')    
def cputype_exists(form, field):
    if form.cpuinstall.data == True :
        if len(form.cputype.data) == 0 :
            raise ValidationError('Please input CPU type')

def memorysize_exists(form, field):
    if form.memoryinstall.data == True :
        if len(form.memorysize.data) == 0 :
            raise ValidationError('Please input Memory size')
def pn_check(form, field):
    basicinfo = PnMap.query.filter_by(pn=form.pn.data.strip())
    if "NRU" in form.pn.data or "PCIe" in form.pn.data:
        return  
    if "LTN" in form.pn.data or "IGT" in form.pn.data:
        return  
    if "PB-" in form.pn.data or "FLYC" in form.pn.data:
        return  
    if basicinfo.count() == 0 and form.packgo.data == False :
        raise ValidationError("Doesn't find this PN in database.")
 
def report_check(form, field):
    #get product basic informatoin
    #Motherboard Serial: BNV7505DN34B1110
    #Bios Version: Build230523
    basicinfo = PnMap.query.filter_by(pn=form.pn.data.strip())
    print(basicinfo.count())
    #get configure information from WorkOrder
    configure = WorkOrder.query.filter_by(wo=form.wo.data, csn=form.csn.data)
    if configure[0].packgo :
        return
    if "NRU" in configure[0].pn or "PCIe" in configure[0].pn: 
        return 
    if "LTN" in configure[0].pn or "IGT" in configure[0].pn: 
        return     
    if "PB-" in configure[0].pn or "FLYC" in configure[0].pn: 
        return         
    #get contents from report file
    contents=form.report.data.split('\n')
    cputype = ""
    mbsn = ""
    mbsn_prefix = ""
    mbsn_sn = ""
    warning = ""
    cancnt = 0
    wlpcnt = 0
    wancnt = 0
    totalnetportcnt = 0
    totalneonetportcnt = 0
    macerrcnt = 0
    mbsnerr = 0
    memorysize_r =[]
    diskssdsize_r =[]
    disknvmesize_r=[]
    #for non pack & go workorder, POC, Nuvo, SEMIL, Nuvis, we will do check
    for line in contents:
        if  "Motherboard Serial" in line :
            #decode motherboard serial number Motherboard Serial: BNV7505DN34B1110
            words = line.split(' ')
            mbsn = words[2].strip()
            print(mbsn)
            print(len(mbsn))
            if len(mbsn) == 16 :
                mbsn_prefix = mbsn[0:8]
                mbsn_sn     = mbsn[8:16]
            else :
                mbsnerr = 1     
            #we will parse MB S/N later
            #POC-40+ Bios Version: EHL.05.43.49.0016
        elif "Bios Version" in line :
            biosver = line.replace("Bios Version:","").strip()
        elif "Bios Release Date" in line :
            biosdate = line.replace("Bios Release Date:","").strip()
            biosdate_obj = datetime.strptime(biosdate,'%m/%d/%Y')
            biosdate = biosdate_obj.strftime("%y%m%d")   
        #enp2s0  (MAC: 78:d0:04:33:40:de) (IPv4: 192.168.61.47) (IPv6: fe80::46be:af:bac0:7c13)
        #docker0  (MAC: 02:42:dd:e3:29:b0) (IPv4: 172.17.0.1)
        #enp0s31f6  (MAC: 78:d0:04:33:40:dd)
        elif "MAC:" in line and "docker" not in line:
            totalnetportcnt = totalnetportcnt + 1
            if "enp" in line and "78:d0:04" in line :
                totalneonetportcnt =  totalneonetportcnt + 1
            elif "enp" in line and "88:88:88:88:87:88" in line :     
                macerrcnt = macerrcnt + 1
            elif "wlx" in line or "wlp" in line or "wlo" in line:
                wlpcnt = wlpcnt + 1    
            elif "can" in line :
                cancnt = cancnt + 1    
            elif "wwan" in line :
                wancnt = wancnt + 1        
        elif "CPU Type" in line:
            #decode and compare cpu type CPU Type: Intel(R) Core(TM) i5-9500TE CPU @ 2.20GHz
            #CPU Type: AMD Ryzen Embedded V1605B with Radeon Vega Gfx
            #For POC, we need't check the CPU type
            if configure[0].cpuinstall and ("POC" in configure[0].pn) == False :
                if "AMD" in line :
                    if "7713P" in line :
                        cputype = "7713P"
                    elif "7003" in line :       
                        cputype = "7003"
                    else :
                        cputype = "na"     
                else :      
                    words = line.split(' ')
                    for wd in words:
                        if ('-' in wd):
                            cputype = wd
        elif (("DIMM" in line) or ("Channel" in line )) and (("DDR" in line ) or ("GB" in line)):
            #decode DDR size anmd compare ChannelA-DIMM0 : 8 GB, DDR4, 3200 MT/s,  Samsung, M471A1K43EB1-CWE, 17FF9947
            words = line.split(' ')
            pos = 0
            for word in words :
                if ("GB" in word) and words[pos-1].isdigit(): 
                    memorysize_r.append(words[pos-1])
                elif ("MB" in word) and words[pos-1].isdigit(): 
                    memorysize_r.append(str(int(int(words[pos-1])/1024)))
                    break
                pos = pos + 1    
        elif (("/dev/nvme" in line )) and ( ("M.2" in line ) or ("Serial" in line)):
            index = contents.index(line) + 1
            words = contents[index].split(' ')
            pos = 0
            for word in words :
                if ("GB" in word and "Size:" in words[pos-2]) : 
                    disknvmesize_r.append(words[pos-1]+"GB")
                    break
                elif ("TB" in word and "Size:" in words[pos-2]) : 
                    disknvmesize_r.append(words[pos-1]+"TB")
                    break
                pos = pos + 1        
        elif ("/dev/sd" in line) and ( ("SATA" in line) or ("M.2" in line) or ("Serial" in line) ):
            index = contents.index(line) + 1
            if "boot" not in contents[index] and "/," not in contents[index]:
                words = line.split(' ')
                pos = 0
                for word in words :
                    if ("GB" in word and "Size:" in words[pos-2]) : 
                        diskssdsize_r.append(words[pos-1]+"GB")
                        break
                    elif ("TB" in word and "Size:" in words[pos-2] ) : 
                        diskssdsize_r.append(words[pos-1]+"TB")
                        break
                    pos = pos + 1            
        elif "can" in line:  
            #compare can 
            cancnt = cancnt + 1
        elif "wlp" in line:
            #compare wifi  
            wlpcnt = wlpcnt + 1
        elif "wwan" in line:
            #compare 4g5g
            wancnt = wancnt + 1
    errorcnt = 0
    errorstr = ""
    memorycnted = 0
    if (configure[0].caninstall) and cancnt == 0 :
        if totalnetportcnt > 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else :     
            errorcnt = errorcnt + 1
            errorstr = errorstr + "CAN not found! "
    if (configure[0].wifiinstall) and wlpcnt == 0 :
        if totalnetportcnt > 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else : 
            errorcnt = errorcnt + 1
            errorstr = errorstr + "Wifi module not found! "
    if (configure[0].fg5ginstall) and wancnt == 0 :
        if totalnetportcnt > 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else : 
            errorcnt = errorcnt + 1
            errorstr = errorstr + "4G5G module not found! "
    if (configure[0].cpuinstall and (cputype.upper().strip() not in configure[0].cputype.upper().strip()))  :
        errorcnt = errorcnt + 1
        errorstr = errorstr + "CPU on Wo is " + configure[0].cputype.upper() + " VS " + cputype.upper()
    if  configure[0].memoryinstall  :
        #parse memory in the workorder 16GBx2
        memorystr = configure[0].memorysize.upper()
        if ("X" in memorystr) :
           memorystr = memorystr.replace("GBX"," ")
           memorystr = memorystr.split(' ')
           memorysize_wo = memorystr[0]
           memorycnt_wo  = memorystr[1]
        else :
           memorysize_wo = memorystr.replace("GB"," ")
           memorycnt_wo  = '1'    
        for mems in memorysize_r:
            if mems.strip() !=  memorysize_wo.strip() :
               errorcnt = errorcnt + 1
               errorstr = errorstr + "Memory size Wo is " + memorysize_wo + "GB VS " + mems + "GB "
            memorycnted = memorycnted + 1          
        if (memorycnted != int(memorycnt_wo)) :
            errorcnt = errorcnt + 1
            errorstr = errorstr + "Memory counter Wo is" +  str(memorycnt_wo) + " VS " +  str(memorycnted)
    if  configure[0].disksize != ""  :
        #parse memory in the workorder SSD256GBx1 NVME1TBx1
        #SSD128GB SSD256GB NVME128GB 
        disksizestr = configure[0].disksize.upper()
        disksizestrs = disksizestr.split(' ')
        disksizessd = []
        disksizenvme = []
        disksizessd0 = []
        disksizenvme0 = []
        for dsz in disksizestrs :
            if ("SSD" in dsz) :
               disksizessd.append(dsz.strip())
            elif ("NVME" in dsz) :
               disksizenvme.append(dsz.strip())
            else:
               disksizessd.append(dsz.strip())    
        for dsz in disksizessd :
            dsz = dsz.replace("SSD","") #SSD256GBX1 -> SS 256GBX1 or SSD256GB -> SS 256GB
            dszs =  dsz.split(' ')
            for ds in dszs :
                if ('X' in ds) :
                    ds = ds.replace("X", " ")
                    dszsn = ds.split(' ')
                    n = int(dszsn[1])
                    disksizessd0.extend([dszsn[0]]*n)
                else:    
                    disksizessd0.append(ds)
        for dsz in disksizenvme :
            dsz = dsz.replace("NVME","") #NVME56GBX1 -> NVM 256GBX1 or NVME256GB -> NVM 256GB
            dszs =  dsz.split(' ')
            for ds in dszs :
                if ('X' in ds) :
                    ds = ds.replace("X", " ")
                    dszsn = ds.split(' ')
                    n = int(dszsn[1])
                    disksizenvme0.extend([dszsn[0]]*n)
                else:    
                    disksizenvme0.append(ds)
        #Compare diskssdsize_r with  disksizessd0
        diskssdsize_rc = []
        for dsz in diskssdsize_r :
            if ("GB" in dsz) :
               size = float(dsz. replace("GB",""))
            else :  
               size = 1000 * float(dsz. replace("TB",""))
            diskssdsize_rc.append(size)   
        diskssdsize_c = []
        for dsz in disksizessd0 :
            if ("GB" in dsz) :
               size = float(dsz. replace("GB",""))
            else :  
               size = 1000 * float(dsz. replace("TB",""))
            diskssdsize_c.append(size)
        #Compare disknvmesize_r with  disksizenvme0        
        disknvmesize_rc = []
        for dsz in disknvmesize_r :
            if ("GB" in dsz) :
               size = float(dsz. replace("GB",""))
            else :  
               size = 1000 * float(dsz. replace("TB",""))
            disknvmesize_rc.append(size)   
        disknvmesize_c = []
        for dsz in disksizenvme0 :
            if ("GB" in dsz) :
               size = float(dsz. replace("GB",""))
            else :  
               size = 1000 * float(dsz. replace("TB",""))
            disknvmesize_c.append(size)
        diskssdmatched = True   
        if len(diskssdsize_rc) != len(diskssdsize_c) :
            diskssdmatched = False
        for dsz in diskssdsize_rc :
            found = False
            pos = 0
            for dsz1 in diskssdsize_c:
                if dsz > (dsz1 * 0.8) and dsz < (dsz1 * 1.05) :
                    found = True
                    diskssdsize_c [pos] = 0
                    break 
            if found == False :
                diskssdmatched = False
                break    
        disknvmematched = True   
        if len(disknvmesize_rc) != len(disknvmesize_c) :
            disknvmematched = False  
        for dsz in disknvmesize_rc :
            found = False 
            pos = 0
            for dsz1 in disknvmesize_c:   
                if dsz > (dsz1 * 0.8) and dsz < (dsz1 * 1.05) :
                    found = True
                    disknvmesize_c [pos] = 0
                    break 
            if found == False :
                disknvmematched = False
                break
        if diskssdmatched == False or disknvmematched == False:
            errorcnt = errorcnt + 1
            errorstr = errorstr + "SSD Disk Wo is" + disksizestr
            errorstr = errorstr + " VS "
            for dsz in diskssdsize_r:
                errorstr += dsz
            for dsz in disknvmesize_r:
                errorstr += dsz
    if  configure[0].disksize == "" and (len(diskssdsize_r) or len(disknvmesize_r)) :
            errorcnt = errorcnt + 1
            errorstr = errorstr + "SSD Disk Wo is 0 VS "
            for dsz in diskssdsize_r:
                errorstr += dsz
            for dsz in disknvmesize_r:
                errorstr += dsz
    #check P/N
    if basicinfo.count() == 0 : 
        errorcnt = errorcnt + 1
        errorstr = errorstr + " P/N not in Database"
    else :
        # check mbsn
        if mbsnerr != 0:
            errorcnt = errorcnt + 1
            errorstr = errorstr + " S/N Error" + mbsn
        elif mbsn_prefix != basicinfo[0].prefix :
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Motherboard not match, was" + mbsn_prefix + "Not" + basicinfo[0].prefix
        #if "BUILD" not in biosver.upper() or  biosver.upper() not in basicinfo[0].biosv.upper():
        if  biosver.upper() not in basicinfo[0].biosv.upper() and biosdate not in basicinfo[0].biosv.upper():
            errorcnt = errorcnt + 1
            errorstr = errorstr + " BIOS version Error"              
        if macerrcnt != 0 :
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Ethernet port MAC address error"
        if totalneonetportcnt < basicinfo[0].net :
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Ethernet ports less"
        if totalneonetportcnt > basicinfo[0].net :
            warning = "WARNING: Ethernet ports quantity not match, maybe preinstalled PCIe card, Please double check!"      
        if totalnetportcnt != (totalneonetportcnt + wlpcnt) :     
            warning = "WARNING: Ethernet ports quantity not match, Please double check!"  
        if totalnetportcnt > 9 :
            warning = "WARNING: Too much Ethernet ports or over 10 ports, Please check manually"         
    form.note.data = warning + form.note.data
    if errorcnt :      
        raise ValidationError(errorstr)
   
class ReportSearchForm(FlaskForm):
    startdate = DateField('Start Date')
    enddate   = DateField('End Date')
    submit    = SubmitField('Search')

class QueryForm(FlaskForm):
    startdate = DateField('Start Date')
    enddate   = DateField('End Date')
    operator  = QuerySelectField('Operator Name', query_factory=get_operateusersname,allow_blank=True)
    wo = StringField('WorkOrder#', validators=[Length(max=100)])
    customers = StringField('Customer Name', validators=[Length(max=100)])
    pn = StringField('Product Model', validators=[Length(max=100)])
    csn = StringField('Chassis S/N', validators=[Length(max=100)])
    packgo = BooleanField('Pack & Go')
    submit    = SubmitField('Search')

class UploadReportForm(FlaskForm):
    wo = StringField('WorkOrder#', render_kw={'readonly': True,'style': 'width: 200px'})
    pn = StringField('Product Model', render_kw={'readonly': True,'style': 'width: 200px'})
    csn = StringField('Chassis S/N', render_kw={'readonly': True,'style': 'width: 200px'})
    msn = StringField('Motherboard S/N', validators=[DataRequired(),Length(max=100)],render_kw={'style': 'width: 200px'})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 300px'})
    mem1 = StringField('Memory Slot1',validators=[Length(max=256)],render_kw={'style': 'width: 300px'})
    mem2 = StringField('Memory Slot2',validators=[Length(max=256)],render_kw={'style': 'width: 300px'})
    mem3 = StringField('Memory Slot3',validators=[Length(max=256)],render_kw={'style': 'width: 300px'})
    mem4 = StringField('Memory Slot4',validators=[Length(max=256)],render_kw={'style': 'width: 300px'})
    gpu1 = StringField('External GPU1',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    gpu2 = StringField('External GPU2',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    sata1 = StringField('SATA1',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    sata2 = StringField('SATA2',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    sata3 = StringField('SATA3',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    sata4 = StringField('SATA4',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    m21 = StringField('M.2 Slot1',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    m22 = StringField('M.2 Slot2',validators=[Length(max=100)],render_kw={'style': 'width: 300px'})
    wifi = StringField('Wifi Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    fg5g = StringField('4G/5G Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    can = StringField('CAN Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    other = StringField('Other Module',validators=[Length(max=100)],render_kw={'style': 'width: 200px'})
    note  = StringField('Notes',validators=[Length(max=256)],widget=TextArea())
    report = StringField('Report File',validators=[Length(max=512000),report_check],widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})
    submit = SubmitField('Update')

class ViewReportForm(FlaskForm):
    wo = StringField('WorkOrder#', render_kw={'readonly': True})
    pn = StringField('Product Model', render_kw={'readonly': True})
    csn = StringField('Chassis S/N', render_kw={'readonly': True})
    msn = StringField('Motherboard S/N', validators=[DataRequired()],render_kw={'readonly': True})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 300px','readonly': True})
    mem1 = StringField('Memory Slot1',render_kw={'style': 'width: 300px', 'readonly': True})
    mem2 = StringField('Memory Slot2',render_kw={'style': 'width: 300px', 'readonly': True})
    mem3 = StringField('Memory Slot3',render_kw={'style': 'width: 300px', 'readonly': True})
    mem4 = StringField('Memory Slot4',render_kw={'style': 'width: 300px',  'readonly': True})
    gpu1 = StringField('External GPU1',render_kw={'readonly': True})
    gpu2 = StringField('External GPU2',render_kw={'readonly': True})
    sata1 = StringField('SATA1',render_kw={'style': 'width: 300px','readonly': True})
    sata2 = StringField('SATA2',render_kw={'style': 'width: 300px','readonly': True})
    sata3 = StringField('SATA3',render_kw={'style': 'width: 300px','readonly': True})
    sata4 = StringField('SATA4',render_kw={'style': 'width: 300px','readonly': True})
    m21 = StringField('M.2 Slot1',render_kw={'style': 'width: 300px','readonly': True})
    m22 = StringField('M.2 Slot2',render_kw={'style': 'width: 300px','readonly': True})
    wifi = StringField('Wifi Module',render_kw={'readonly': True})
    fg5g = StringField('4G/5G Module',render_kw={'readonly': True})
    can = StringField('CAN Module',render_kw={'readonly': True})
    other = StringField('Other Module',render_kw={'readonly': True})
    note  = StringField('Notes',widget=TextArea(),render_kw={'readonly': True})
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})
    

class ReviewReportForm(FlaskForm):
    wo = StringField('WorkOrder#', render_kw={'readonly': True})
    pn = StringField('Product Model', render_kw={'readonly': True})
    csn = StringField('Chassis S/N', render_kw={'readonly': True})
    msn = StringField('Motherboard S/N', validators=[DataRequired()],render_kw={'readonly': True})
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 300px','readonly': True})
    mem1 = StringField('Memory Slot1',render_kw={'style': 'width: 300px', 'readonly': True})
    mem2 = StringField('Memory Slot2',render_kw={'style': 'width: 300px', 'readonly': True})
    mem3 = StringField('Memory Slot3',render_kw={'style': 'width: 300px', 'readonly': True})
    mem4 = StringField('Memory Slot4',render_kw={'style': 'width: 300px',  'readonly': True})
    gpu1 = StringField('External GPU1',render_kw={'readonly': True})
    gpu2 = StringField('External GPU2',render_kw={'readonly': True})
    sata1 = StringField('SATA1',render_kw={'style': 'width: 300px','readonly': True})
    sata2 = StringField('SATA2',render_kw={'style': 'width: 300px','readonly': True})
    sata3 = StringField('SATA3',render_kw={'style': 'width: 300px','readonly': True})
    sata4 = StringField('SATA4',render_kw={'style': 'width: 300px','readonly': True})
    m21 = StringField('M.2 Slot1',render_kw={'style': 'width: 300px','readonly': True})
    m22 = StringField('M.2 Slot2',render_kw={'style': 'width: 300px','readonly': True})
    wifi = StringField('Wifi Module',render_kw={'readonly': True})
    fg5g = StringField('4G/5G Module',render_kw={'readonly': True})
    can = StringField('CAN Module',render_kw={'readonly': True})
    other = StringField('Other Module',render_kw={'readonly': True})
    note  = StringField('Notes',widget=TextArea(),render_kw={'readonly': True})
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})
    action = SelectField('Approve or Deny',choices=[('0','Approve'),('1','Deny')])
    submit = SubmitField('Confirm')
  

class ReviewReportFileForm(FlaskForm):
    
    report = StringField('Report File',widget=TextArea(),render_kw={'style': 'width: 400px','readonly': True})

class AddWorkorderForm(FlaskForm):
    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)])
    ldtime= DateField('Lead Time')
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=600),wocsn_exists], widget=TextArea())
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists])
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists])
    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)')
    cpuinstall = BooleanField('CPU Installation')
    memoryinstall = BooleanField('Memory Installation')
    gpuinstall = BooleanField('GPU Installation')
    wifiinstall = BooleanField('Wifi Installation')
    caninstall = BooleanField('CAN Installation')
    mezioinstall = BooleanField('MezIO Installation')
    fg5ginstall = BooleanField('4G5G Installation')
    osinstall = StringField('Installation OS Name', validators=[Length(max=100)])
    packgo = BooleanField('Pack & Go')
    operator = QuerySelectField('Operator Name', query_factory=get_operateusersname,allow_blank=True)
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    csid= HiddenField('Creator ID')
    cstime=HiddenField('Creating Time')
    tktime=HiddenField('Take Time')
    status= HiddenField('Status')
    submit = SubmitField('Create New WorkOrder')

class EditOneComputerForm(FlaskForm):
    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)])
    ldtime= DateField('Lead Time')
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)])
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists])
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists])
    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)')
    cpuinstall = BooleanField('CPU Installation')
    memoryinstall = BooleanField('Memory Installation')
    gpuinstall = BooleanField('GPU Installation')
    wifiinstall = BooleanField('Wifi Installation')
    caninstall = BooleanField('CAN Installation')
    mezioinstall = BooleanField('MezIO Installation')
    fg5ginstall = BooleanField('4G5G Installation')
    osinstall = StringField('Installation OS Name', validators=[Length(max=100)])
    packgo = BooleanField('Pack & Go')
    operator = QuerySelectField('Operator Name', query_factory=get_operateusersname,allow_blank=True)
    asid= HiddenField('Assembler ID')
    insid= HiddenField('Inspector ID')
    astime=HiddenField('Assembling Time')
    intime=HiddenField('Inspection Time')
    csid= HiddenField('Creator ID')
    cstime=HiddenField('Creating Time')
    status= HiddenField('Status')
    submit = SubmitField('Update')

class ReviewOneComputerForm(FlaskForm):

    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    ldtime= DateField('Lead Time',render_kw={'readonly': True})
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)],render_kw={'readonly': True})
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists],render_kw={'readonly': True})
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists],render_kw={'readonly': True})
    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)',render_kw={'readonly': True})
    cpuinstall = BooleanField('CPU Installation',render_kw={'readonly': True})
    memoryinstall = BooleanField('Memory Installation',render_kw={'readonly': True})
    gpuinstall = BooleanField('GPU Installation',render_kw={'readonly': True})
    wifiinstall = BooleanField('Wifi Installation',render_kw={'readonly': True})
    caninstall = BooleanField('CAN Installation',render_kw={'readonly': True})
    mezioinstall = BooleanField('MezIO Installation',render_kw={'readonly': True})
    fg5ginstall = BooleanField('4G5G Installation',render_kw={'readonly': True})
    osinstall = StringField('Installation OS Name', validators=[Length(max=100)],render_kw={'readonly': True})
    packgo = BooleanField('Pack & Go',render_kw={'readonly': True})
    #operator = QuerySelectField('Operator Name', query_factory=get_operateusersname,allow_blank=True,render_kw={'readonly': True})
    biosver = StringField('BIOS Version',render_kw={'readonly': True})
    sopver  = StringField('SOP Version',render_kw={'readonly': True})
    submit = SubmitField('Return')