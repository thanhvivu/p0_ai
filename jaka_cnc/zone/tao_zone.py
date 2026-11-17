# Generates zone_check.txt (sub-program block) and sim_zone_test.txt (simulation test).
import re, sys
main_src, outdir = sys.argv[1], sys.argv[2]
XU='(0.7056980154 * ({t}[0] - 345.833) + 0.7085118376 * ({t}[1] + 489.782) + 0.0011344638 * ({t}[2] + 136.233))'
YU='(-0.7085100607 * ({t}[0] - 345.833) + 0.7056988446 * ({t}[1] + 489.782) - 0.0016231544 * ({t}[2] + 136.233))'
xu=lambda t: XU.format(t=t); yu=lambda t: YU.format(t=t)

init = [
'# ===== ZONE CHECK - INIT (run once, after the taught points are declared) =====',
'# Robot working-zone bits for the PLC. TCP is converted from Base to usrfr_thanh',
'# [345.833,-489.782,-136.233,-0.093,-0.065,45.114] inside each if(), because this',
'# controller rejects arithmetic in assignments. Not a safety function.',
'# DO56 idx55 = robot inside odd CNC side  (X_user > zone_x_door1, CNC1/3/5)',
'# DO57 idx56 = robot inside even CNC side (X_user < zone_x_door2, CNC2/4/6)',
'# DO58 idx57 = robot inside Pick/supply zone (Y_user past y_pick - margin, toward Pick)',
'# Constants can be tuned here; they are approximate on purpose.',
'zone_x_door1 = 679.362',
'zone_x_door2 = -365.358',
'zone_pick_margin = 50.0',
'zone_pick_tcp = kine_forward(p_pick)',
'zone_home_tcp = kine_forward(p_home_location)',
'# Pick side along Y_user is detected from HomeLocation: +1 Pick has larger Y, -1 smaller Y.',
'zone_pick_side = 1',
'if(%s < %s):' % (yu('zone_pick_tcp'), yu('zone_home_tcp')),
'    zone_pick_side = -1',
'end',
'zone_odd = 0','zone_even = 0','zone_pick = 0',
'zone_odd_last = -1','zone_even_last = -1','zone_pick_last = -1',
]
check = [
'# ===== ZONE CHECK - CALL (repeat as often as possible) =====',
'zone_tcp = get_atl_tcp_pose()',
'zone_odd = 0',
'if(%s > zone_x_door1):' % xu('zone_tcp'),
'    zone_odd = 1',
'end',
'zone_even = 0',
'if(%s < zone_x_door2):' % xu('zone_tcp'),
'    zone_even = 1',
'end',
'zone_pick = 0',
'if(zone_pick_side == 1):',
'    if(%s > %s - zone_pick_margin):' % (yu('zone_tcp'), yu('zone_pick_tcp')),
'        zone_pick = 1',
'    end',
'else:',
'    if(%s < %s + zone_pick_margin):' % (yu('zone_tcp'), yu('zone_pick_tcp')),
'        zone_pick = 1',
'    end',
'end',
'# Write a DO only when its state changes; literal values only.',
]
for var,last,idx,name in [('zone_odd','zone_odd_last',55,'DO56 ODD CNC ZONE'),('zone_even','zone_even_last',56,'DO57 EVEN CNC ZONE'),('zone_pick','zone_pick_last',57,'DO58 PICK ZONE')]:
    check += ['zone_chg = 1',
              'if(%s == %s):'%(var,last), '    zone_chg = 0', 'end',
              'if(zone_chg == 1):',
              '    if(%s == 1):'%var,
              '        set_digital_output(4,%d,1,1)'%idx, '        log_message(1,"%s ON")'%name,
              '    else:',
              '        set_digital_output(4,%d,0,1)'%idx, '        log_message(1,"%s OFF")'%name,
              '    end',
              'end',
              '%s = %s'%(last,var)]

def dd(l):
    t=l.split('#')[0].strip()
    if re.match(r'^(if|while)\s*\(',t): return 1
    if t=='end': return -1
    return 0
def check_ok(lines,name):
    d=0
    for x in lines:
        d+=dd(x); assert d>=0,name
    assert d==0,name
    assert not any(re.search(r'"[^"]*[()][^"]*"',x) for x in lines),name

hdr=['# ===================================================================',
'# ZONE CHECK SUB-PROGRAM - robot working-zone bits DO56/DO57/DO58 for the PLC',
'# Part 1 (INIT) once after the point declarations, Part 2 (CALL) repeatedly.',
'# Needs p_pick and p_home_location from the main program.',
'# ===================================================================','']
blk=hdr+init+['']+check+['']
check_ok(init,'init'); check_ok(check,'check')
open(outdir+'/zone_check.txt','w',newline='').write('\r\n'.join(blk))

# ---- simulation test: header of main program + init + visit points + call ----
L=open(main_src).read().replace('\r','').split('\n')
he=[i for i,l in enumerate(L) if l.startswith('# Reset common and Process interlock outputs')][0]
def stub(lines):
    out=[]
    for l in lines:
        ind=l[:len(l)-len(l.lstrip())]
        if l.strip().startswith('set_digital_output('):
            out.append(ind+'sleep(0.01)')
        else: out.append(l)
    return out
tests=[('p_home_location','HOMELOCATION','ODD 0 EVEN 0'),('p_pick_true_axis','PICKWAIT','PICK 1 if within margin'),
       ('p_pick','PICK','PICK 1'),('p_home_location','HOMELOCATION','PICK 0'),
       ('p_door_c1','DOORC1','ODD 0 or flicker - on boundary'),('p_odd_load_wait','C1LOADWAIT','ODD 1'),
       ('p_odd_load','C1LOAD','ODD 1'),('p_door_c1','DOORC1','ODD back to 0'),
       ('p_door_c2','DOORC2','EVEN 0 or flicker - on boundary'),('p_even_load_wait','LOADM2_WAIT','EVEN 1'),
       ('p_even_load','LOADC2','EVEN 1'),('p_door_c2','DOORC2','EVEN back to 0'),
       ('p_home_location','HOMELOCATION','all 0')]
t=['# !!! SIMULATION ONLY !!! Zone-check test: DO writes replaced by sleep, states are logged.','']+L[:he]+['']+init+[
 'log_message(1,"SIM ZONE TEST START")']
for k,(p,n,e) in enumerate(tests,1):
    t+=['log_message(1,"SIM ZONE %d MOVE TO %s EXPECT %s")'%(k,n,e.replace('-',' ')),
        'movj(%s,0,speed_movej_fast,720,0)'%p]+stub(check)+[
        'if(zone_odd == 1):','    log_message(1,"SIM ZONE STATE ODD 1")','else:','    log_message(1,"SIM ZONE STATE ODD 0")','end',
        'if(zone_even == 1):','    log_message(1,"SIM ZONE STATE EVEN 1")','else:','    log_message(1,"SIM ZONE STATE EVEN 0")','end',
        'if(zone_pick == 1):','    log_message(1,"SIM ZONE STATE PICK 1")','else:','    log_message(1,"SIM ZONE STATE PICK 0")','end']
t+=['log_message(1,"SIM ZONE TEST END")','']
check_ok(t,'sim')
open(outdir+'/sim_zone_test.txt','w',newline='').write('\r\n'.join(t))
print('ok', len(blk), len(t))
