import re, sys
src, outdir = sys.argv[1], sys.argv[2]
L=open(src).read().replace('\r','').split('\n')
def dd(l):
    t=l.split('#')[0].strip()
    if re.match(r'^(if|while)\s*\(',t): return 1
    if t=='end': return -1
    return 0
def block_from(i):
    d=0
    for j in range(i,len(L)):
        d+=dd(L[j])
        if d==0: return L[i:j+1]
def dedent(lines):
    n=min(len(x)-len(x.lstrip()) for x in lines if x.strip())
    return [x[n:] if x.strip() else '' for x in lines]
def indent(lines,k): return [(' '*k+x) if x.strip() else '' for x in lines]
def stub(lines):
    out=[]
    skip=0
    for l in lines:
        if skip:
            skip+=dd(l)
            continue
        if re.match(r'^while\(di\d+ == 0\):$',l.strip()):
            skip=1          # drop the whole DI polling loop (its body only re-reads the DI)
            continue
        ind=l[:len(l)-len(l.lstrip())]
        s=l.strip()
        if re.match(r'^set_digital_output\(4,',s) or re.match(r'^set_analog_output\(4,',s):
            out.append(ind+'sleep(0.01)'); continue
        m=re.match(r'^wait_input\(4,(\d+),1,0\)$',s)
        if m:
            out.append(ind+'log_message(1,"SIM SKIP WAIT DI%d")'%(int(m.group(1))+1)); out.append(ind+'sleep(0.3)'); continue
        m=re.match(r'^(di\d+) = get_digital_input\(4,(\d+)\)$',s)
        if m:
            # do not assign the diXX variable at all (controller rejected 'di64 = 1')
            out.append(ind+'log_message(1,"SIM SKIP WAIT DI%d")'%(int(m.group(2))+1)); out.append(ind+'sleep(0.3)'); continue
        l=l.replace('get_analog_input(4,15)','sim_ai16')
        assert 'get_digital_input' not in l and 'wait_input' not in l and 'get_analog_input' not in l, l
        out.append(l)
    return out

hdr_end=[i for i,l in enumerate(L) if l.startswith('# Reset common and Process interlock outputs')][0]
header=L[:hdr_end]
# active-set selection block (the 3 if-blocks after the comment inside the Case execution)
ci=[i for i,l in enumerate(L) if l.strip()=='if(cnc_motion_case > 0):']
sel_start=ci[0]+2   # skip 'if(...)' and comment line
sel=[]; i=sel_start
for _ in range(3):
    b=block_from(i); sel+=b; i+=len(b)
sel=dedent(sel)
motion=dedent(block_from(ci[1]))
h0=[i for i,l in enumerate(L) if l.strip()=='home_actual_joint = get_atl_joint_pose()'][0]
h1=[i for i,l in enumerate(L) if 'DO16 ON ROBOT AT HOME WAIT DI90 OFF' in l][0]
home=dedent(L[h0:h1+2])
assert sum(dd(x) for x in home)==0 and sum(dd(x) for x in motion)==0 and sum(dd(x) for x in sel)==0

WARN=['# ===================================================================',
'# !!! SIMULATION ONLY - DO NOT RUN ON THE REAL ROBOT IN NORMAL MODE !!!',
'# All PLC handshakes (DI waits) are skipped and all DO/AO writes are removed.',
'# Generated automatically from jamaguchi_cnc36.txt (motion/Home code copied unchanged).',
'# Re-generate after editing points so the test uses the same values.',
'# ===================================================================']

# ---------- 1. motion dry run ----------
m=WARN+['# SIM TEST 1: Case 29..32 (Load/Unload odd and even CNC) for pair 1, 2, 3.',
'# Each Case: enter by its Door -> Case motion -> leave by the same Door, like DI16 exit.','']+header+[
'','log_message(1,"SIM MOTION TEST START")',
'movj(p_home_location,0,speed_movej_fast,720,0)',
'sim_pair = 1','sim_next = 0','sim_case = 0',
'while(sim_pair > 0):','    cnc_pair = sim_pair']+indent(sel,4)+[
'    sim_case = 29',
'    while(sim_case > 0):',
'        cnc_motion_case = sim_case','        case_motion_ok = 1',
'        door_select = 2',
'        if(sim_case == 29):','            door_select = 1','        end',
'        if(sim_case == 30):','            door_select = 1','        end',
'        if(door_select == 1):','            log_message(1,"SIM ENTRY DOOR ODD")','            movj(p_odd_door,0,speed_movej_fast,720,0)',
'        else:','            log_message(1,"SIM ENTRY DOOR EVEN")','            movj(p_even_door,0,speed_movej_fast,720,0)','        end']+indent(stub(motion),8)+[
'        if(door_select == 1):','            log_message(1,"SIM EXIT DOOR ODD")','            movj(p_odd_door,0,speed_movej_fast,720,0)',
'        else:','            log_message(1,"SIM EXIT DOOR EVEN")','            movj(p_even_door,0,speed_movej_fast,720,0)','        end',
'        sim_next = 0',
'        if(sim_case == 29):','            sim_next = 30','        end',
'        if(sim_case == 30):','            sim_next = 31','        end',
'        if(sim_case == 31):','            sim_next = 32','        end',
'        sim_case = sim_next',
'    end',
'    movj(p_home_location,0,speed_movej_fast,720,0)',
'    log_message(1,"SIM PAIR DONE")',
'    sim_next = 0',
'    if(sim_pair == 1):','        sim_next = 2','    end',
'    if(sim_pair == 2):','        sim_next = 3','    end',
'    sim_pair = sim_next',
'end',
'log_message(1,"SIM MOTION TEST END")','']

# ---------- 2. Home recovery ----------
tests=[('p_c1_load_end',1,'C1LOADEND'),('p_c1_load',1,'C1LOAD'),('p_c1_load_wait',1,'C1LOADWAIT'),
('p_c1_unload',1,'C1UNLOAD'),('p_c1_unload_wait',1,'C1UNLOADWAIT'),('p_c1_unload_down',1,'C1UNLOAD - DOWN POINT EQUALS UNLOAD POINT'),
('p_end_load_m2v1',2,'ENDLOADM2V1'),('p_load_c2',2,'LOADC2'),('p_load_m2_wait',2,'LOADM2_WAIT'),
('p_unload_m2',2,'UNLOADM2'),('p_unload_m2_wait',2,'UNLOADM2_WAIT'),('p_air_c2',2,'AIRC2'),
('p_door_c1',1,'DOORC1'),('p_door_c2',2,'DOORC2'),
('p_c3_load',3,'C1LOAD PAIR CNC3 CNC4'),('p_c4_load_end',4,'ENDLOADM2V1 PAIR CNC3 CNC4'),
('p_c5_unload',5,'C1UNLOAD PAIR CNC5 CNC6'),('p_c6_unload_wait',6,'UNLOADM2_WAIT PAIR CNC5 CNC6'),
('p_load_c2',2,'NONE - CNC2 DANGER LOAD TOOL ROUTE VIA LOADM2_WAIT','lift'),
('p_unload_m2',2,'NONE - CNC2 DANGER UNLOAD TOOL ROUTE VIA UNLOADM2_WAIT','lift'),
('p_c1_load',1,'NONE - CNC1 DANGER LOAD TOOL ROUTE VIA C1LOADWAIT','lift'),
('p_c1_unload',1,'NONE - CNC1 DANGER UNLOAD TOOL ROUTE VIA C1UNLOADWAIT','lift'),
('p_air_switch_tool',1,'NONE - CNC1 DANGER AIR TOOL ROUTE VIA AIRC1V1'),
('p_air_c2v1',2,'NONE - CNC2 DANGER AIR TOOL ROUTE VIA AIRC2V1')]
h=WARN+['# SIM TEST 2: DI90 Home recovery from each taught point.',
'# For each test: MoveJ HomeLocation -> MoveJ straight to the test point (simulation only:',
'# no obstacle check) -> run the unchanged DI90 Home block with AI16 = sim_ai16.',
'# Compare "SIM EXPECT ..." with the next "HOME ACTUAL POSITION MATCH ..." log.','']+header+[
'','log_message(1,"SIM HOME TEST START")','sim_ai16 = 0','sim_t = 1','sim_next = 0',
'# 40 mm above a taught point: outside the 20 mm match window, still in front of the chuck',
'sim_up = [0.0,0.0,40.0,0.0,0.0,0.0]',
'while(sim_t > 0):',
'    movj(p_home_location,0,speed_movej_fast,720,0)',
'    home_route_door_done = 0','    home_already_home = 0','    home_route_hint = 0']
for k,t in enumerate(tests,1):
    p,ai,exp=t[:3]
    h+=['    if(sim_t == %d):'%k,'        sim_ai16 = %d'%ai,
        '        log_message(1,"SIM TEST %d EXPECT MATCH %s AI16 %d")'%(k,exp,ai),
        '        movj(%s,0,speed_movej_fast,720,0)'%p]
    if len(t)>3:
        h+=['        sim_pose = kine_forward(%s)'%p,'        sim_pose = pose_add(sim_pose,sim_up)',
            '        movl(sim_pose,0,30,200,0)']
    h+=['    end']
h+=indent(stub(home),4)+['    sim_next = 0']
for k in range(1,len(tests)):
    h+=['    if(sim_t == %d):'%k,'        sim_next = %d'%(k+1),'    end']
h+=['    sim_t = sim_next','end','log_message(1,"SIM HOME TEST END")','']

# ---------- 3. P8 change tool ----------
ce=[i for i,l in enumerate(L) if '# Case execution point' in l][0]
p8i=[i for i in range(ce,len(L)) if L[i].strip()=='if(active_process == 8):'][0]
p8=dedent(block_from(p8i))
t3=WARN+['# SIM TEST 3: P8 Change Tool (dao tool) motion, unchanged except IO stubs.',
'# Expected: UNLOAD_DAOTOOL_WAIT -> UNLOAD_DAOTOOL -> back -> TRUNGGIAN -> LOAD_DAOTOOL_WAIT',
'# -> MOVEL straight down 30 mm to LOAD_DAOTOOL -> back -> HOMELOCATION.','']+header+[
'','log_message(1,"SIM P8 TEST START")',
'movj(p_home_location,0,speed_movej_fast,720,0)',
'active_process = 8','active_case = 54','case_motion_ok = 1']+stub(p8)+[
'log_message(1,"SIM P8 TEST END")','']

for name,txt in [('sim_test1_motion.txt',m),('sim_test2_home.txt',h),('sim_test3_p8.txt',t3)]:
    assert not any(re.search(r'"[^"]*[()][^"]*"',x) for x in txt), 'parentheses inside a string: JAKA parser rejects them'
    assert sum(dd(x) for x in txt)==0, name
    d=0
    for x in txt:
        d+=dd(x); assert d>=0
    open(outdir+'/'+name,'w',newline='').write('\r\n'.join(txt))
    print(name,len(txt),'lines')
