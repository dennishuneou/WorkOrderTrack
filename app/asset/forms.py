from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, SelectField, ValidationError,BooleanField, DateField,IntegerField, FloatField
from wtforms.validators import DataRequired, Length, InputRequired, NumberRange
from wtforms.fields.html5 import DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import TextArea
from app.asset.models import WorkOrder, Production, PnMap, PackageBox, QualityLog
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
    if "PCIe" in form.pn.data:
        return  
    if "LTN" in form.pn.data or "IGT" in form.pn.data:
        return  
    if "PB-" in form.pn.data:
        return  
    if basicinfo.count() == 0 and form.packgo.data == False :
        raise ValidationError("Doesn't find this PN in database.")
def pack_pn_check(form, field):
    basicinfo = PnMap.query.filter_by(pn=form.computer.data.strip())
    if basicinfo.count() == 0 :
        raise ValidationError("Doesn't find this Product in database.")        
def DuplicateCheck(form, field):
    basicinfo = PnMap.query.filter_by(pn=form.pn.data.strip())
    if basicinfo.count() :
        raise ValidationError("Product Name Duplicate") 
def report_check(form, field):
    import re
    #get product basic informatoin
    #Motherboard Serial: BNV7505DN34B1110
    #Bios Version: Build230523
    basicinfo = PnMap.query.filter_by(pn=form.pn.data.strip())
    print(basicinfo.count())
    #get configure information from WorkOrder
    configure = WorkOrder.query.filter_by(wo=form.wo.data, csn=form.csn.data)
    if configure[0].packgo :
        return
    if "PCIe" in configure[0].pn: 
        return 
    if "LTN" in configure[0].pn or "IGT" in configure[0].pn: 
        return     
    if "PB-" in configure[0].pn: 
        return        
    if len(form.report.data.strip()) == 0 :
        return
    #Load Jetson SOM part number mappings from productmap.txt
    jetson_som_mapping = {}
    try:
        with open('/home/neousys/Testopencode/productmap.txt', 'r') as f:
            for line in f:
                #Parse lines like: 'GC-Jetson-AGX32GB-Orin-Nvidia' key message is 'AGX32GB-Orin' part number is '699-13701-0004'
                #Handle case where key message might have trailing comma: 'AGX64GB-Orin, part number is...'
                match = re.search(r"'([^']+)'\s+key message is\s+'([^']+)'[,]?\s+part number is\s+'([^']+)'", line)
                if match:
                    full_name = match.group(1)
                    key_message = match.group(2).rstrip(',')  # Remove trailing comma if present
                    part_number = match.group(3)
                    #Map both full name and key message to part number
                    jetson_som_mapping[full_name] = part_number
                    jetson_som_mapping[key_message] = part_number
    except Exception as e:
        print("Error loading productmap.txt: " + str(e))
    
    #Hard-coded x86 GPU mappings from GPU.txt
    #Map device_id -> list of {part_number, key_message}
    gpu_device_to_parts = {
        '25B6': [{'part_number': 'GC-A2-NVD', 'key_message': 'A2'}],
        '1C82': [{'part_number': 'GC-GTX-1050Ti-Gigabyte', 'key_message': 'GTX-1050Ti'}],
        '1C03': [{'part_number': 'GC-GTX-1060-EVGA', 'key_message': 'GTX-1060'}],
        '1B80': [{'part_number': 'GC-GTX-1080-ASUS', 'key_message': 'GTX-1080'}, {'part_number': 'GC-GTX-1080-ASUS-ZeroV', 'key_message': 'GTX-1080'}],
        '1B06': [{'part_number': 'GC-GTX-1080Ti-MSI', 'key_message': 'GTX-1080Ti'}],
        '1F82': [{'part_number': 'GC-GTX-1650-MSI', 'key_message': 'GTX-1650'}, {'part_number': 'GC-GTX-1650-ZOTAC', 'key_message': 'GTX-1650'}, {'part_number': 'GC-GTX-1650_D6-MSI', 'key_message': 'GTX-1650'}],
        '21C4': [{'part_number': 'GC-GTX-1660S-Gigabyte', 'key_message': 'GTX-1660S'}, {'part_number': 'GC-GTX-1660S-O6G-ASUS', 'key_message': 'GTX-1660S'}],
        '2182': [{'part_number': 'GC-GTX-1660Ti-6G-ASUS', 'key_message': 'GTX-1660Ti'}, {'part_number': 'GC-GTX-1660Ti-ASUS', 'key_message': 'GTX-1660Ti'}, {'part_number': 'GC-GTX-1660Ti-Gigabyte', 'key_message': 'GTX-1660Ti'}, {'part_number': 'GC-GTX1660Ti-ZTC', 'key_message': 'GTX-1660Ti'}],
        '22C1': [{'part_number': 'GC-L4-Nvidia', 'key_message': 'L4'}],
        '1EB5': [{'part_number': 'GC-P2200-Leadtek', 'key_message': 'P2200'}, {'part_number': 'GC-QUADRO-P2200-PNY', 'key_message': 'Quadro P2200'}],
        '1CB1': [{'part_number': 'GC-QUADRO-P1000-PNY', 'key_message': 'Quadro P1000'}],
        '1BB1': [{'part_number': 'GC-QUADRO-P4000-PNY', 'key_message': 'Quadro P4000'}],
        '1CB6': [{'part_number': 'GC-QUADRO-P620-PNY', 'key_message': 'Quadro P620'}],
        '1F08': [{'part_number': 'GC-RTX-2060-ASUS', 'key_message': 'RTX 2060'}],
        '1E84': [{'part_number': 'GC-RTX-2070S-EVGA', 'key_message': 'RTX 2070 Super'}],
        '1E82': [{'part_number': 'GC-RTX-2080-EVGA', 'key_message': 'RTX 2080'}, {'part_number': 'GC-RTX-2080-EVGA-BK', 'key_message': 'RTX 2080'}],
        '1E81': [{'part_number': 'GC-RTX-2080S-EVGA', 'key_message': 'RTX 2080 Super'}, {'part_number': 'GC-RTX-2080S-EVGA-BK', 'key_message': 'RTX 2080 Super'}, {'part_number': 'GC-RTX-2080S-EVGA-KO', 'key_message': 'RTX 2080 Super'}, {'part_number': 'GC-RTX-2080S-Leadtek', 'key_message': 'RTX 2080 Super'}, {'part_number': 'GC-RTX-2080S-NVD', 'key_message': 'RTX 2080 Super'}],
        '1E07': [{'part_number': 'GC-RTX-2080Ti-EVGA', 'key_message': 'RTX 2080Ti'}, {'part_number': 'GC-RTX-2080Ti-EVGA-BK', 'key_message': 'RTX 2080Ti'}, {'part_number': 'GC-RTX-2080Ti-NVD', 'key_message': 'RTX 2080Ti'}],
        '2503': [{'part_number': 'GC-RTX-3060-EVGA-BK', 'key_message': 'RTX 3060'}, {'part_number': 'GC-RTX3060-ZTC', 'key_message': 'RTX 3060'}],
        '2486': [{'part_number': 'GC-RTX-3060Ti-ZTC', 'key_message': 'RTX 3060Ti'}],
        '2484': [{'part_number': 'GC-RTX-3070-2XOC-MSI', 'key_message': 'RTX 3070'}, {'part_number': 'GC-RTX3070-GAMING-OC-GABE', 'key_message': 'RTX 3070'}, {'part_number': 'GC-RTX3070-OC-GABE', 'key_message': 'RTX 3070'}],
        '1EB1': [{'part_number': 'GC-RTX-4000-PNY', 'key_message': 'RTX 4000 (Turing)'}, {'part_number': 'GC-RTX4000-LT', 'key_message': 'RTX 4000 (Turing)'}],
        '2507': [{'part_number': 'GC-RTX3050-OC-MSI', 'key_message': 'RTX 3050'}, {'part_number': 'GC-RTX3050-PNY', 'key_message': 'RTX 3050'}],
        '2941': [{'part_number': 'GC-RTX-5080-NVD', 'key_message': 'RTX 5080'}, {'part_number': 'GC-RTX5080-OC-MSI', 'key_message': 'RTX 5080'}, {'part_number': 'GC-RTX5080-OC-PLUS-MSI', 'key_message': 'RTX 5080'}],
        '2870': [{'part_number': 'GC-RTX2000Ada-Nvidia', 'key_message': 'RTX 2000 Ada'}, {'part_number': 'GC-RTX2000Ada-Nvidia-601', 'key_message': 'RTX 2000 Ada'}, {'part_number': 'GC-RTX2000Ada-PNY', 'key_message': 'RTX 2000 Ada'}, {'part_number': 'GC-RTX2000EAda-PNY', 'key_message': 'RTX 2000E Ada'}],
        '2786': [{'part_number': 'GC-RTX4070-OC-MSI', 'key_message': 'RTX 4070'}, {'part_number': 'GC-RTX4070-OCV2-GABE', 'key_message': 'RTX 4070'}, {'part_number': 'GC-RTX4070-OC-MSI', 'key_message': 'RTX 4070'}],
        '2783': [{'part_number': 'GC-RTX4070SUPER-OC-MSI', 'key_message': 'RTX 4070 Super'}],
        '2782': [{'part_number': 'GC-RTX4070Ti-OC-MSI', 'key_message': 'RTX 4070Ti'}],
        '2206': [{'part_number': 'GC-RTX-3080-12GB-ASUS', 'key_message': 'RTX 3080'}, {'part_number': 'GC-RTX3080-Tnity-ZTC', 'key_message': 'RTX 3080'}, {'part_number': 'GC-RTX3080-TnityOC-ZTC', 'key_message': 'RTX 3080'}, {'part_number': 'GC-RTX3080-TnityOCLHR-ZTC', 'key_message': 'RTX 3080'}],
        '27B0': [{'part_number': 'GC-RTX4000Ada-PNY', 'key_message': 'RTX 4000 Ada'}, {'part_number': 'GC-RTX4000SFFAda-PNY', 'key_message': 'RTX 4000 SFF Ada'}, {'part_number': 'GC-RTXPRO4000SFF-LT', 'key_message': 'RTX PRO 4000 SFF'}, {'part_number': 'GC-RTXPRO4000SFF-PNY', 'key_message': 'RTX PRO 4000 SFF'}],
        '2882': [{'part_number': 'GC-RTX4060-GABE', 'key_message': 'RTX 4060'}, {'part_number': 'GC-RTX4060-LT', 'key_message': 'RTX 4060'}],
        '2684': [{'part_number': 'GC-RTX4080', 'key_message': 'RTX 4080'}, {'part_number': 'GC-RTX4080-OC-MSI', 'key_message': 'RTX 4080'}],
        '2703': [{'part_number': 'GC-RTX4080 SUPER-OC-MSI', 'key_message': 'RTX 4080 Super'}, {'part_number': 'GC-RTX4080S-LT', 'key_message': 'RTX 4080 Super'}],
        '2730': [{'part_number': 'GC-RTX4500Ada-PNY', 'key_message': 'RTX 4500 Ada'}],
        '2708': [{'part_number': 'GC-RTX5000Ada-PNY', 'key_message': 'RTX 5000 Ada'}],
        '2D83': [{'part_number': 'GC-RTX5050-SOLO-ZTC', 'key_message': 'RTX 5050'}],
        '2D05': [{'part_number': 'GC-RTX5060-SOLO-ZTC', 'key_message': 'RTX 5060'}],
        '2946': [{'part_number': 'GC-RTX5070-OC-MSI', 'key_message': 'RTX 5070'}],
        '2944': [{'part_number': 'GC-RTX5070Ti-OC-MSI', 'key_message': 'RTX 5070Ti'}],
        '2901': [{'part_number': 'GC-RTX5090-OC-MSI', 'key_message': 'RTX 5090'}],
        '26B1': [{'part_number': 'GC-RTX6000Ada-PNY', 'key_message': 'RTX 6000 Ada'}, {'part_number': 'GC-RTX6000Ada-PNY-601', 'key_message': 'RTX 6000 Ada'}, {'part_number': 'GC-RTXPRO6000-PNY', 'key_message': 'RTX PRO 6000'}],
        '25B0': [{'part_number': 'GC-RTXA1000-8GB-LT', 'key_message': 'RTX A1000'}, {'part_number': 'GC-RTXA1000-8GB-PNY', 'key_message': 'RTX A1000'}],
        '25B1': [{'part_number': 'GC-RTXA2000-12GB-LT', 'key_message': 'RTX A2000'}, {'part_number': 'GC-RTXA2000-12GB-PNY', 'key_message': 'RTX A2000'}],
        '24B0': [{'part_number': 'GC-RTXA4000-LT', 'key_message': 'RTX A4000'}, {'part_number': 'GC-RTXA4000-LT1', 'key_message': 'RTX A4000'}, {'part_number': 'GC-RTXA4000-PNY', 'key_message': 'RTX A4000'}],
        '24B1': [{'part_number': 'GC-RTXA4500-LT', 'key_message': 'RTX A4500'}, {'part_number': 'GC-RTXA4500-PNY', 'key_message': 'RTX A4500'}],
        '2231': [{'part_number': 'GC-RTXA5000-LT', 'key_message': 'RTX A5000'}, {'part_number': 'GC-RTXA5000-PNY', 'key_message': 'RTX A5000'}],
        '2230': [{'part_number': 'GC-RTXA6000-LT', 'key_message': 'RTX A6000'}, {'part_number': 'GC-RTXA6000-PNY', 'key_message': 'RTX A6000'}],
        '2D30': [{'part_number': 'GC-RTXPRO2000-PNY', 'key_message': 'RTX PRO 2000'}],
        '1FF2': [{'part_number': 'GC-T1000-8GB-PNY', 'key_message': 'T1000'}],
        '1BB3': [{'part_number': 'GC-TESLA-P4-NVD', 'key_message': 'Tesla P4'}],
        '1EB8': [{'part_number': 'GC-TESLA-T4-NVD', 'key_message': 'Tesla T4'}],
    }
    
    #Map part_number -> device info
    gpu_part_to_device = {}
    for device_id, part_list in gpu_device_to_parts.items():
        for part_info in part_list:
            gpu_part_to_device[part_info['part_number']] = {
                'key_message': part_info['key_message'],
                'device_id': device_id
            }
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
    biosver = ""
    biosdate = ""
    memorysize_r =[]
    diskssdsize_r =[]
    disknvmesize_r=[]
    #Jetson variables
    is_jetson = False
    jetson_som_part = ""
    jetson_som_part_found = False
    jetson_som_part_line_count = 0
    jetson_cpu_info = ""
    jetson_cputype_key = ""
    jetson_som_main = ""  #e.g., "699-13701-00" from line 72
    jetson_som_extra = ""  #e.g., "05" from line 73 (ignore version)
    #x86 GPU variables
    gpu_device_ids = []
    gpu_detected_parts = []
    #for non pack & go workorder, POC, Nuvo, SEMIL, Nuvis, we will do check
    for line in contents:
        if "CPU Info:" in line and "Jetson" in line:
            #Detect Jetson system
            is_jetson = True
            jetson_cpu_info = line.replace("CPU Info:","").strip()
        if "SOM part number" in line:
            jetson_som_part_found = True
            jetson_som_part_line_count = 0
        #Accumulate SOM part number lines after "SOM part number" header
        if jetson_som_part_found and "****" not in line and "SOM part number" not in line:
            jetson_som_part_line_count += 1
            if jetson_som_part_line_count <= 3:
                #Parse SOM part number from hex dump format
                #Line 72: "10: ... 699-13701-00"
                #Line 73: "20: ... 05-502" (502 is version, ignore it)
                #Full part number: 699-13701-0005 (00 from line 72 + 05 from line 73)
                
                #Try to find the main pattern on line 72: ddd-ddddd-dd
                match = re.search(r'(\d{3}-\d{5}-\d{2})', line)
                if match:
                    jetson_som_main = match.group(1)  # e.g., "699-13701-00"
                else:
                    #Try to find continuation on line 73: dd (just the first two digits before version)
                    match = re.search(r'(\d{2})-\d{3}\s*$', line)
                    if match:
                        jetson_som_extra = match.group(1)  # e.g., "05"
        
        #Detect x86 GPU from NVIDIA Corporation Device XXXX lines
        if not is_jetson:
            gpu_match = re.search(r'NVIDIA Corporation Device ([0-9a-fA-F]{4})', line)
            if gpu_match:
                device_id = gpu_match.group(1).upper()
                if device_id not in gpu_device_ids:
                    gpu_device_ids.append(device_id)
                    print("Detected GPU device ID: " + device_id)
        if  "Motherboard Serial" in line :
            #decode motherboard serial number
            #x86 format: Motherboard Serial: BNV7505DN34B1110 (space after colon)
            #Jetson format: Motherboard Serial:1794325052023 (no space after colon)
            mbsn = line.replace("Motherboard Serial:","").strip()
            print(mbsn)
            print(len(mbsn))
            if len(mbsn) == 16 :
                mbsn_prefix = mbsn[0:8]
                mbsn_sn     = mbsn[8:16]
            elif len(mbsn) == 13 :
                mbsn_sn = mbsn 
            elif "SER" not in configure[0].pn:
                mbsnerr = 1     
            #we will parse MB S/N later
            #POC-40+ Bios Version: EHL.05.43.49.0016
        elif "Bios Version" in line and not is_jetson:
            biosver = line.replace("Bios Version:","").strip()
        elif "Bios Release Date" in line and not is_jetson:
            biosdate = line.replace("Bios Release Date:","").strip()
            biosdate_obj = datetime.strptime(biosdate,'%m/%d/%Y')
            biosdate = biosdate_obj.strftime("%y%m%d")   
        #enp2s0  (MAC: 78:d0:04:33:40:de) (IPv4: 192.168.61.47) (IPv6: fe80::46be:af:bac0:7c13)
        #docker0  (MAC: 02:42:dd:e3:29:b0) (IPv4: 172.17.0.1)
        #enp0s31f6  (MAC: 78:d0:04:33:40:dd)
        elif "link/MAC:" in line and "docker" not in line:
            #Jetson format: "link/MAC: 78:d0:04:39:83:27 brd ff:ff:ff:ff:ff"
            totalnetportcnt = totalnetportcnt + 1
            line_lower = line.lower()
            if ("78:d0:04" in line_lower or "3c:6d:66" in line_lower or "48:b0:2d" in line_lower):
                totalneonetportcnt =  totalneonetportcnt + 1
            elif "9c:6b:00" in line_lower:
                totalneonetportcnt =  totalneonetportcnt + 1
            elif "88:88:88:88:87:88" in line_lower :     
                macerrcnt = macerrcnt + 1
            elif "wl" in line_lower:
                wlpcnt = wlpcnt + 1    
            elif "can" in line_lower:
                cancnt = cancnt + 1        
            elif "wwan" in line_lower:
                wancnt = wancnt + 1        
        elif "MAC:" in line and "docker" not in line:
            #x86 format: "enp2s0  (MAC: 78:d0:04:33:40:de)"
            totalnetportcnt = totalnetportcnt + 1
            line_lower = line.lower()
            if "enp" in line and ("78:d0:04" in line_lower or "3c:6d:66" in line_lower or "48:b0:2d" in line_lower) :
                totalneonetportcnt =  totalneonetportcnt + 1
            elif "enp" in line and "9c:6b:00" in line_lower :
                totalneonetportcnt =  totalneonetportcnt + 1
            elif "enx" in line and "MAC:" in line :
                totalneonetportcnt =  totalneonetportcnt + 1    
            elif "enp" in line and "88:88:88:88:87:88" in line_lower :     
                macerrcnt = macerrcnt + 1
            elif "wlx" in line or "wlp" in line or "wlo" in line:
                wlpcnt = wlpcnt + 1    
            elif "can0" in line or "can1" in line or "can2" in line or "can3" in line:
                cancnt = cancnt + 1    
            elif "can4" in line or "can5" in line or "can6" in line or "can7" in line:
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
                        cputype = line.replace("CPU Type:","")    
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
         #X86 computer       
        elif  not is_jetson and ("/dev/nvme" in line ) and ( ("M.2" in line ) or ("Serial" in line)): 
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
#/dev/sda Phison SSBP064GTMC0-S91 Serial: 16507B0642015 Size: 59.6 GB
#sda1 (/media/neousys/A2AC-44B2, vfat, 479 MB)
#sda2 (/media/neousys/e5cf18bd-8282-43aa-97f7-9ea59bcad9f9, ext4, 33.6 GB)
#sda3 (/boot/efi, vfat, 511 MB)
#sda4 (/, ext4, 23.5 GB)
        #X86 computer  
        elif ("/dev/sd" in line) and ( ("SATA" in line) or ("M.2" in line) or ("Serial" in line) ) and not is_jetson: 
            index = contents.index(line) + 1
            if "boot" not in contents[index] and "media" not in contents[index] and "/," not in contents[index]:
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
    #Combine SOM part number from collected lines (for Jetson)
    if is_jetson and jetson_som_main and jetson_som_extra:
        #jetson_som_main = "699-13701-00", jetson_som_extra = "05"
        #Full part number: "699-13701-0005"
        jetson_som_part = jetson_som_main + jetson_som_extra
        print("Combined SOM part: " + jetson_som_part)
        #Clean up: extract just the part number
        match = re.search(r'(\d{3}-\d{5}-\d{4})', jetson_som_part)
        if match:
            jetson_som_part = match.group(1)
            print("Final SOM part: " + jetson_som_part)
    #Process Jetson disk info if needed (separate from x86)
    if is_jetson:
        #Clear x86 disk arrays and re-parse for Jetson format
        disknvmesize_r = []
        diskssdsize_r = []
        for line in contents:
            if ("/dev/nvme" in line) and "Size:" in line:
                #Jetson NVMe: /dev/nvme0n1 Size:1.9TB E: ID_SERIAL=...
                words = line.split()
                for word in words:
                    if "Size:" in word:
                        size = word.split(':', 1)[1]
                        disknvmesize_r.append(size)
                        break
            elif ("/dev/mmcblk" in line):
                #Skip eMMC onboard storage for Jetson
                pass
            elif ("/dev/sd" in line) and "Size:" in line:
                #Jetson SATA: skip USB, /dev/sdb Size:28.7GB E: ID_SERIAL=...
                if "USB" not in line:
                    words = line.split()
                    for word in words:
                        if "Size:" in word:
                            size = word.split(':', 1)[1]
                            diskssdsize_r.append(size)
                            break
    errorcnt = 0
    errorstr = ""
    memorycnted = 0
    if (configure[0].caninstall  or configure[0].withcan) and cancnt == 0 :
        if totalnetportcnt + cancnt > 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else :     
            errorcnt = errorcnt + 1
            errorstr = errorstr + "CAN not found! "
    if (configure[0].wifiinstall or configure[0].withwifi) and wlpcnt == 0 :
        if totalnetportcnt + cancnt> 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else : 
            errorcnt = errorcnt + 1
            errorstr = errorstr + "Wifi module not found! "
    if (configure[0].fg5ginstall or configure[0].withfg5g) and wancnt == 0 :
        if totalnetportcnt + cancnt> 9 :
            warning = "WARNING: Too much Ethernet ports, Please check manual"     
        else : 
            errorcnt = errorcnt + 1
            errorstr = errorstr + "4G5G module not found! "
    if is_jetson:
        #For Jetson systems, validate SOM part number against cputype
        if configure[0].cpuinstall:
            if jetson_som_part:
                #Clean up jetson_som_part to get just the part number
                match = re.search(r'(\d{3}-\d{5}-\d{4})', jetson_som_part)
                if match:
                    jetson_som_part = match.group(1)
                #Look up expected part number using cputype from WorkOrder
                cputype_full = configure[0].cputype.strip()
                expected_part = jetson_som_mapping.get(cputype_full, "")
                if not expected_part:
                    #Try with just the key message part
                    cputype_key = cputype_full
                    #Extract key message like "AGX32GB-Orin" from "GC-Jetson-AGX32GB-Orin-Nvidia"
                    match = re.search(r'Jetson-([A-Za-z0-9\-]+)-Nvidia', cputype_full, re.IGNORECASE)
                    if match:
                        cputype_key = match.group(1)
                        expected_part = jetson_som_mapping.get(cputype_key, "")
                if expected_part:
                    if jetson_som_part != expected_part:
                        errorcnt = errorcnt + 1
                        errorstr = errorstr + "Jetson SOM part number mismatch! Expected: " + expected_part + " Got: " + jetson_som_part
                else:
                    print("Jetson SOM part: " + jetson_som_part + ", CPU Type: " + cputype_full + " (no mapping found)")
            else:
                errorcnt = errorcnt + 1
                errorstr = errorstr + "Jetson SOM part number not found in report! "
    else:
        if (configure[0].cpuinstall and (cputype.upper().strip() not in configure[0].cputype.upper().strip()))  :
            errorcnt = errorcnt + 1
            errorstr = errorstr + "CPU on Wo is " + configure[0].cputype.upper() + " VS " + cputype.upper()
        
        #Validate x86 GPU against work order
        if configure[0].gpuinstall and configure[0].gpu.strip():
            #Parse GPU from work order (e.g., "RTX4080X2" or "RTX4080")
            gpu_wo = configure[0].gpu.strip().upper()
            print("Work order GPU: " + gpu_wo)
            
            #Parse quantity if specified (e.g., "RTX4080X2" or "GC-RTX5050-SOLO-ZTCx1" -> 1 card)
            gpu_qty_expected = 1
            gpu_part_expected = gpu_wo
            #Use regex to match trailing [xX]\d+ pattern for quantity
            qty_match = re.search(r'[xX](\d+)$', gpu_wo)
            if qty_match:
                gpu_qty_expected = int(qty_match.group(1))
                gpu_part_expected = gpu_wo[:qty_match.start()]
            
            #Look up expected part number from GPU.txt
            if gpu_part_expected in gpu_part_to_device:
                expected_info = gpu_part_to_device[gpu_part_expected]
                expected_device_id = expected_info['device_id']
                expected_key_message = expected_info['key_message']
                print("Expected GPU: " + expected_key_message + " (Device ID: " + expected_device_id + ")")
                print("Detected GPU device IDs: " + str(gpu_device_ids))
                
                #Check if detected GPU matches
                if not gpu_device_ids:
                    errorcnt = errorcnt + 1
                    errorstr = errorstr + "GPU not found in report! "
                else:
                    #Count matching GPUs
                    matching_gpus = [d for d in gpu_device_ids if d == expected_device_id]
                    if len(matching_gpus) == 0:
                        errorcnt = errorcnt + 1
                        errorstr = errorstr + "GPU mismatch! Expected: " + expected_key_message + " (Device ID: " + expected_device_id + ")"
                        errorstr = errorstr + " Detected: " + str(gpu_device_ids) + " "
                    elif len(matching_gpus) != gpu_qty_expected:
                        errorcnt = errorcnt + 1
                        errorstr = errorstr + "GPU quantity mismatch! Expected: " + str(gpu_qty_expected) + "x " + expected_key_message
                        errorstr = errorstr + " Detected: " + str(len(matching_gpus)) + "x " + expected_device_id + " "
            else:
                print("WARNING: GPU part '" + gpu_part_expected + "' not found in GPU.txt")
    if  configure[0].memoryinstall  or configure[0].memorysize.strip():
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
                if(dsz.strip()): 
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
                pos = pos + 1
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
                pos = pos + 1    
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
        elif not is_jetson and mbsn_prefix not in basicinfo[0].prefix :
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Motherboard not match, was" + mbsn_prefix + "Not" + basicinfo[0].prefix
        #if "BUILD" not in biosver.upper() or  biosver.upper() not in basicinfo[0].biosv.upper():
        if not is_jetson and biosver.upper() not in basicinfo[0].biosv.upper() and biosdate not in basicinfo[0].biosv.upper():
            errorcnt = errorcnt + 1
            errorstr = errorstr + " BIOS version Error"              
        if macerrcnt != 0 :
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Ethernet port MAC address error"
        if totalneonetportcnt < basicinfo[0].net and totalnetportcnt < 10:
            errorcnt = errorcnt + 1
            errorstr = errorstr + " Ethernet ports less"
            print(totalneonetportcnt)
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
    cpu = StringField('CPU', validators=[DataRequired()],render_kw={'style': 'width: 300px','readonly': False})
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
    m21 = StringField('M.2 Slot1',render_kw={'style': 'width: 300px','readonly': False})
    m22 = StringField('M.2 Slot2',render_kw={'style': 'width: 300px','readonly': False})
    wifi = StringField('Wifi Module',render_kw={'readonly': True})
    fg5g = StringField('4G/5G Module',render_kw={'readonly': True})
    can = StringField('CAN Module',render_kw={'readonly': True})
    other = StringField('Other Module',render_kw={'readonly': True})
    note  = StringField('Notes',widget=TextArea(),render_kw={'readonly': False})
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
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=2000),wocsn_exists], widget=TextArea())
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists])
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists])
    
    gpu = StringField('GPU(etc: RTX4080X2)',validators=[Length(max=100)])
    withwifi = BooleanField('Including Wifi')
    withcan  = BooleanField('Including CAN')
    withfg5g = BooleanField('Including 4G/5G Module')
    ospreinstalled = BooleanField('OS Preinstalled')
    osactivation = BooleanField('OS Activation')
    diskpreinstalled = BooleanField('Disk Preinstalled')

    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)')
    cpuinstall = BooleanField('CPU Installation,uncheck if preinstalled')
    memoryinstall = BooleanField('Memory Installation,uncheck if preinstalled')
    gpuinstall = BooleanField('GPU Installation,uncheck if preinstalled')
    wifiinstall = BooleanField('Wifi Installation,uncheck if preinstalled')
    caninstall = BooleanField('CAN Installation,uncheck if preinstalled')
    mezioinstall = BooleanField('MezIO Installation,uncheck if preinstalled')
    fg5ginstall = BooleanField('4G5G Installation,uncheck if preinstalled')
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
    doc_items = StringField('Doc Items (separated by |)', validators=[Length(max=512)], render_kw={'placeholder': 'e.g., GPU-RTX4080|SSD256GB|WIFI'})
    submit = SubmitField('Create New WorkOrder')

class EditOneComputerForm(FlaskForm):
    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)])
    ldtime= DateField('Lead Time')
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)])
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists])
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists])
    
    gpu = StringField('GPU(etc: RTX4080X2)',validators=[Length(max=100)])
    withwifi = BooleanField('Including Wifi')
    withcan  = BooleanField('Including CAN')
    withfg5g = BooleanField('Including 4G/5G Module')
    ospreinstalled = BooleanField('OS Preinstalled')
    osactivation = BooleanField('OS Activation')
    diskpreinstalled = BooleanField('Disk Preinstalled')

    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)')
    cpuinstall = BooleanField('CPU Installation,uncheck if preinstalled')
    memoryinstall = BooleanField('Memory Installation,uncheck if preinstalled')
    gpuinstall = BooleanField('GPU Installation,uncheck if preinstalled')
    wifiinstall = BooleanField('Wifi Installation,uncheck if preinstalled')
    caninstall = BooleanField('CAN Installation,uncheck if preinstalled')
    mezioinstall = BooleanField('MezIO Installation,uncheck if preinstalled')
    fg5ginstall = BooleanField('4G5G Installation,uncheck if preinstalled')
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
    doc_items = StringField('Doc Items (separated by |)', validators=[Length(max=512)], render_kw={'placeholder': 'e.g., GPU-RTX4080|SSD256GB|WIFI'})
    submit = SubmitField('Update')

class ReviewOneComputerForm(FlaskForm):

    wo = StringField('WorkOrder#', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    ldtime= DateField('Lead Time',render_kw={'readonly': True})
    customers = StringField('Customer Name', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)],render_kw={'readonly': True})
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)],render_kw={'readonly': True})
    cputype = StringField('CPU (etc: i9-12900E)',validators=[Length(max=100),cputype_exists],render_kw={'readonly': True})
    memorysize = StringField('Memory(etc: 16GBX2)',validators=[Length(max=100),memorysize_exists],render_kw={'readonly': True})
    
    gpu = StringField('GPU(etc: RTX4080X2)',validators=[Length(max=100)])
    withwifi = BooleanField('Including Wifi')
    withcan  = BooleanField('Including CAN')
    withfg5g = BooleanField('Including 4G/5G Module')
    ospreinstalled = BooleanField('OS Preinstalled')
    osactivation = BooleanField('OS Activation')
    diskpreinstalled = BooleanField('Disk Preinstalled')

    disksize = StringField('Disk(etc: SSD256GBx1 NVME1TBx1)',render_kw={'readonly': True})
    cpuinstall = BooleanField('CPU Installation,uncheck if preinstalled',render_kw={'readonly': True})
    memoryinstall = BooleanField('Memory Installation,uncheck if preinstalled',render_kw={'readonly': True})
    gpuinstall = BooleanField('GPU Installation,uncheck if preinstalled',render_kw={'readonly': True})
    wifiinstall = BooleanField('Wifi Installation,uncheck if preinstalled',render_kw={'readonly': True})
    caninstall = BooleanField('CAN Installation,uncheck if preinstalled',render_kw={'readonly': True})
    mezioinstall = BooleanField('MezIO Installation,uncheck if preinstalled',render_kw={'readonly': True})
    fg5ginstall = BooleanField('4G5G Installation,uncheck if preinstalled',render_kw={'readonly': True})
    osinstall = StringField('Installation OS Name,uncheck if preinstalled', validators=[Length(max=100)],render_kw={'readonly': True})
    packgo = BooleanField('Pack & Go',render_kw={'readonly': True})
    #operator = QuerySelectField('Operator Name', query_factory=get_operateusersname,allow_blank=True,render_kw={'readonly': True})
    biosver = StringField('BIOS Version',render_kw={'readonly': True})
    sopver  = StringField('SOP Version',render_kw={'readonly': True})
    submit = SubmitField('Return')

class AddProductForm(FlaskForm):

    pn = StringField('Product Number', validators=[DataRequired(),DuplicateCheck,Length(max=100)])
    sop = StringField('SOP Document', validators=[DataRequired(),Length(max=100)])
    biosv = StringField('BIOS Version(etc:SL13A003.Build240711)', validators=[DataRequired(),Length(max=100)])
    prefix= StringField('MSN prefix(etc:BSL13010 SL130100)', validators=[DataRequired(),Length(max=20)]) 
    net = IntegerField('Number of ethernet ports', validators=[InputRequired(),NumberRange(min=0,max=20)]) 
    poe = IntegerField('Support PoE(etc:1)', validators=[InputRequired(),NumberRange(min=0,max=1)]) 
    ign = IntegerField('Support IGN(etc:1)', validators=[InputRequired(),NumberRange(min=0,max=1)]) 
    unitsinabox = IntegerField('Maximum Units in an outer box', validators=[DataRequired(),NumberRange(min=1,max=100)])  
    buildpoints = IntegerField('Build points', validators=[InputRequired(),NumberRange(min=0,max=100)])   
    testonlypoints = IntegerField('Test Only points', validators=[InputRequired(),NumberRange(min=0,max=30)])   
    gpu =  IntegerField('GPU installation points', validators=[InputRequired(),NumberRange(min=0,max=30)])   
    extra =  FloatField('Extra points', validators=[InputRequired()])   
    customizedBIOS = BooleanField('Customized BIOS')
    customizedSOP = BooleanField('Customized SOP')
    customizedOSImage = BooleanField('Customized OS Image')
    customizedMechincal = BooleanField('Customized Mechanical')
    customizedPackage = BooleanField('Customized Package')
    customizedLabel = BooleanField('Customized Lable')

    abbreviation = StringField('Abbreviation', validators=[Length(max=32)])
    options = [('NRU','NRU'),('SEMIL','SEMIL'),('COMPUTER','COMPUTER'),('CABLEKIT','CABLEKIT'),('CARD','CARD'),('FANKIT','FANKIT'),('CAMERA','CAMERA'),('PB','PB-UNIT'),('POWERADAPTOR','POWER ADAPTOR'),('DINRAIL','DINRAIL'),('WALLMOUNT','WALLMOUNT'),('DUMPINGBRACKET','DUMPINGBRACKET'),('GPU','GPU')]
    category = SelectField('Category', choices= options,validators=[InputRequired(),Length(max=16)])
    height = FloatField('Height(inches)', validators=[InputRequired()])
    width = FloatField('Width(inches)', validators=[InputRequired()])
    thickness = FloatField('Thickness(inches)', validators=[InputRequired()])
    weight = FloatField('Weight(pounds)', validators=[InputRequired()])
    inneraccessory = StringField('Inner Accessory', validators=[Length(max=256)])
    notes = StringField('Notes', validators=[Length(max=256)], widget=TextArea())

    submit    = SubmitField('Add')   

class EditProductForm(FlaskForm):
    pn = StringField('Product Number', validators=[DataRequired(),Length(max=100)])
    sop = StringField('SOP Document', validators=[DataRequired(),Length(max=100)])
    biosv = StringField('BIOS Version(etc:SL13A003.Build240711)', validators=[DataRequired(),Length(max=100)])
    prefix= StringField('MSN prefix(etc:BSL13010 SL130100)', validators=[DataRequired(),Length(max=20)]) 
    net = IntegerField('Number of ethernet ports', validators=[InputRequired(),NumberRange(min=0,max=20)]) 
    #DataRequireed not work with 0
    poe = IntegerField('Support PoE(etc:1)', validators=[InputRequired(),NumberRange(min=0,max=1)]) 
    ign = IntegerField('Support IGN(etc:1)', validators=[InputRequired(),NumberRange(min=0,max=1)]) 
    unitsinabox = IntegerField('Maximum Units in an outer box', validators=[DataRequired(),NumberRange(min=1,max=100)])  
    buildpoints = IntegerField('Build points', validators=[InputRequired(),NumberRange(min=0,max=100)])   
    testonlypoints = IntegerField('Test Only points', validators=[InputRequired(),NumberRange(min=0,max=30)])   
    gpu =  IntegerField('GPU installation points', validators=[InputRequired(),NumberRange(min=0,max=30)])   
    extra =  IntegerField('Extra points', validators=[InputRequired(),NumberRange(min=0,max=30)])   
    customized =  IntegerField('Customized ', validators=[InputRequired(),NumberRange(min=0,max=4096)])

    abbreviation = StringField('Abbreviation', validators=[Length(max=32)])
    category = StringField('Category NRU,PB,COMPUTER, CARD', validators=[InputRequired(),Length(max=16)])
    height = FloatField('Height(inches)', validators=[InputRequired()])
    width = FloatField('Width(inches)', validators=[InputRequired()])
    thickness = FloatField('Thickness(inches)', validators=[InputRequired()])
    weight = FloatField('Weight(pounds)', validators=[InputRequired()])
    inneraccessory = StringField('Inner Accessory', validators=[Length(max=256)])
    notes = StringField('Notes', validators=[Length(max=256)], widget=TextArea())

    submit    = SubmitField('Update')   
    #customizedBIOS = BooleanField('Customized BIOS')
    #customizedSOP = BooleanField('Customized SOP')
    #customizedOSImage = BooleanField('Customized OS Image')
    #customizedMechincal = BooleanField('Customized Mechanical')
    #customizedPackage = BooleanField('Customized Package')
    #customizedLabel = BooleanField('Customized Lable')
class QueryProductsForm(FlaskForm):
    pn = StringField('Product Model', validators=[Length(max=100)])
    submit    = SubmitField('Search')   
class QueryWorkordersForm(FlaskForm):
    wo = StringField('WorkOrder', validators=[Length(max=100)])
    submit    = SubmitField('Search')   

class PackingCalculateForm(FlaskForm):
    
    #computer = QuerySelectField('Computer',query_factory =lambda: PnMap.query.filter_by(category='COMPUTER').order_by(PnMap.pn).all()+PnMap.query.filter_by(category='PB').order_by(PnMap.pn).all()+PnMap.query.filter_by(category='NRU').order_by(PnMap.pn).all()+PnMap.query.filter_by(category='SEMIL').order_by(PnMap.pn).all(), get_label='pn', allow_blank=True)
    computer = StringField('Computer', validators=[DataRequired(),pack_pn_check,Length(max=100)])
    qty_computer = IntegerField('Computer Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=1) 
    
    dinrail = QuerySelectField('DIN RAIL',query_factory =lambda: PnMap.query.filter_by(category='DINRAIL').all(), get_label='pn', allow_blank=True)
    qty_dinrail = IntegerField('DIN RAIL Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    dmpbr = QuerySelectField('DumpingBracket',query_factory =lambda: PnMap.query.filter_by(category='DUMPINGBRACKET').all(), get_label='pn', allow_blank=True)
    qty_dmpbr = IntegerField('DMPBR Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    fankit = QuerySelectField('FANkit',query_factory =lambda: PnMap.query.filter_by(category='FANKIT').all(), get_label='pn', allow_blank=True)
    qty_fankit = IntegerField('FANkit Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    wallmount = QuerySelectField('Wallmount',query_factory =lambda: PnMap.query.filter_by(category='WALLMOUNT').all(), get_label='pn', allow_blank=True)
    qty_wallmount = IntegerField('Wallmount Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    card1 = QuerySelectField('PCIe Card 1',query_factory =lambda: PnMap.query.filter_by(category='CARD').all(), get_label='pn', allow_blank=True)
    qty_card1 = IntegerField('PCIe Card 1 Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    card2 = QuerySelectField('PCIe Card 2',query_factory =lambda: PnMap.query.filter_by(category='CARD').all(), get_label='pn', allow_blank=True)
    qty_card2 = IntegerField('PCIe Card 2 Quantity', validators=[InputRequired(),NumberRange(min=0,max=1000)],default=0) 
    
    gpu = QuerySelectField('GPU',query_factory =lambda: PnMap.query.filter_by(category='GPU').all(), get_label='pn', allow_blank=True)
    qty_gpu = IntegerField('GPU Quantity', validators=[InputRequired(),NumberRange(min=0,max=2000)],default=0) 
    
    poweradaptor = QuerySelectField('Power Adaptor',query_factory =lambda: PnMap.query.filter_by(category='POWERADAPTOR').all(), get_label='pn', allow_blank=True)
    qty_poweradaptor = IntegerField('Power Adaptor Quantity', validators=[InputRequired(),NumberRange(min=0,max=2000)],default=0) 
    
    cablekit1 = QuerySelectField('CableKit1',query_factory =lambda: PnMap.query.filter_by(category='CABLEKIT').all(), get_label='pn', allow_blank=True)
    qty_cablekit1 = IntegerField('Cablekit1 Quantity', validators=[InputRequired(),NumberRange(min=0,max=2000)],default=0) 
    
    cablekit2 = QuerySelectField('CableKit2',query_factory =lambda: PnMap.query.filter_by(category='CABLEKIT').all(), get_label='pn', allow_blank=True)
    qty_cablekit2 = IntegerField('Cablekit2 Quantity', validators=[InputRequired(),NumberRange(min=0,max=2000)],default=0) 
    
    camera = QuerySelectField('Camera',query_factory =lambda: PnMap.query.filter_by(category='CAMERA').all(), get_label='pn', allow_blank=True)
    qty_camera = IntegerField('Camera Quantity', validators=[InputRequired(),NumberRange(min=0,max=2000)],default=0)

    submit = SubmitField('Calculate')

class AddQualityLogForm(FlaskForm):
    options = [('Production Line','Production Line'),('RMA','RMA'),('IQC','IQC'),('IPQC/FQC','IPQC/FQC')]
    source = SelectField('Source(Production,RMA,IQC)',  choices= options,validators=[InputRequired(),Length(max=100)])
    wo = StringField('WO or RMA or Invoice', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)])
    options = [('Motherboard','Motherboard'),('Daughterboard','Daughterboard'),('Chassis','Chassis'),('CPU','CPU'),('MEMORY','MEMORY'),('DISK','DISK'),('MODULES','MODULE'),('Package','Package')]
    defectpart = SelectField('Defect Part', choices= options,validators=[DataRequired(),Length(max=100)])
    defectpartsn = StringField('Defect Part SN(or NA)', validators=[DataRequired(),Length(max=100)])
    reason = StringField('Issue Description', validators=[DataRequired(),Length(max=300)],widget=TextArea())
    submit = SubmitField('Create New Quality Log')
       
class QueryQlogForm(FlaskForm):
    startdate = DateField('Start Date')
    enddate   = DateField('End Date')
    options = [('All','All'),('Production Line','Production Line'),('RMA','RMA'),('IQC','IQC'),('IPQC/FQC','IPQC/FQC')]
    source = SelectField('Source',  choices= options,validators=[InputRequired(),Length(max=100)])
    options = [('All','All'),('New','New'),('Processing','Processing'),('Pending','Pending'),('Closed','Closed')]
    status = SelectField('Status',  choices= options,validators=[InputRequired(),Length(max=100)])
    submit    = SubmitField('Search')

class EditQualityLogForm(FlaskForm):
    options = [('Production Line','Production Line'),('RMA','RMA'),('IQC','IQC'),('IPQC/FQC','IPQC/FQC')]
    source = SelectField('Source(Production,RMA,IQC)',  choices= options,validators=[InputRequired(),Length(max=100)])
    wo = StringField('WO or RMA or Invoice', validators=[DataRequired(),Length(max=100)])
    pn = StringField('Product Model', validators=[DataRequired(),pn_check,Length(max=100)])
    csn = StringField('Chassis Serial Number', validators=[DataRequired(),Length(max=100)])
    options = [('Motherboard','Motherboard'),('Daughterboard','Daughterboard'),('Chassis','Chassis'),('CPU','CPU'),('MEMORY','MEMORY'),('DISK','DISK'),('MODULES','MODULE'),('Package','Package')]
    defectpart = SelectField('Defect Part', choices= options,validators=[DataRequired(),Length(max=100)])
    defectpartsn = StringField('Defect Part SN(or NA)', validators=[DataRequired(),Length(max=100)])
    reason = StringField('Issue Description', validators=[DataRequired(),Length(max=300)],widget=TextArea())
    options = [('New','New'),('Processing','Processing'),('Pending','Pending'),('Closed','Closed')]
    status = SelectField('Case status(New,Processing,Pending,Closed)', choices= options,validators=[DataRequired(),Length(max=100)])
    conclusion = StringField('Case Conclusion', validators=[Length(max=100)])
    processlog = StringField('Process Log', render_kw={'readonly': True},widget=TextArea())
    newaction = StringField('New Action Log',validators=[Length(max=200)],widget=TextArea())
    submit = SubmitField('Update Quality Log')
