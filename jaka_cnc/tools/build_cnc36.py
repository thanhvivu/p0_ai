import re, sys
src, dst = sys.argv[1], sys.argv[2]
L = open(src).read().split('\n')   # LF-normalized original
def ln(n): return L[n-1]
NEW2={120:('p_load_m2_wait = [50.293,126.775,63.817,171.018,-264.506,44.650]','p_load_m2_wait = [51.875,125.469,65.840,169.996,-261.814,44.043]'),
      122:('p_load_c2 = [56.589,126.376,64.481,170.780,-258.211,44.831]','p_load_c2 = [57.542,125.553,65.891,169.886,-256.149,44.176]'),
      124:('p_end_load_m2v1 = [56.678,126.378,64.477,170.783,-258.123,44.833]','p_end_load_m2v1 = [57.997,125.599,65.829,169.904,-255.694,44.187]')}
for n,(o,nw) in NEW2.items():
    assert L[n-1].strip()==o,(n,L[n-1]); L[n-1]=nw
# ---- [CNC36] P8: Load_daotool points re-taught 2026-11 + MoveL Wait -> Load_daotool ----
P8={145:('p_load_daotool_wait = [-5.425,91.023,100.495,165.202,-140.160,-48.016]','p_load_daotool_wait = [-4.269,92.626,96.069,174.039,-139.051,-43.430]'),
    146:('p_load_daotool = [-5.425,91.909,104.011,160.800,-140.159,-48.016]','p_load_daotool = [-4.267,94.590,103.932,164.212,-139.049,-43.430]'),
    149:('p_unload_daotool = [-53.520,77.575,108.245,85.260,-89.523,-323.554]','p_unload_daotool = [-53.447,77.544,108.268,85.268,-89.522,-323.481]'),
    154:('p_unload_daotool_segment_min = [-58.520,72.391,97.652,80.260,-94.672,-328.554]','p_unload_daotool_segment_min = [-58.447,72.391,97.652,80.268,-94.672,-328.481]'),
    155:('p_unload_daotool_segment_max = [-48.210,82.575,113.245,96.290,-84.523,-318.161]','p_unload_daotool_segment_max = [-48.210,82.544,113.268,96.290,-84.522,-318.161]'),
    152:('p_load_daotool_segment_min = [-10.425,86.023,95.495,155.800,-145.160,-53.016]','p_load_daotool_segment_min = [-9.269,87.626,91.069,159.212,-144.051,-48.430]'),
    153:('p_load_daotool_segment_max = [-0.425,96.909,109.011,170.202,-135.159,-43.016]','p_load_daotool_segment_max = [0.733,99.590,108.932,179.039,-134.049,-38.430]')}
for n,(o,nw) in P8.items():
    assert L[n-1].strip()==o,(n,L[n-1]); L[n-1]=nw
T26={75:('p_pick_true_axis = [-62.562,148.695,10.785,199.567,-197.644,-45.829]','p_pick_true_axis = [-62.955,153.356,0.661,205.147,-198.542,-47.273]'),
     77:('p_pick = [-62.566,144.864,23.441,190.741,-197.648,-45.829]','p_pick = [-62.988,145.634,22.030,191.501,-198.575,-47.272]'),
     114:('p_c1_unload_wait = [-138.163,142.907,33.696,184.325,-275.438,-135.035]','p_c1_unload_wait = [-138.024,143.229,32.752,184.947,-274.933,-136.083]'),
     115:('p_c1_unload = [-133.563,140.802,37.750,182.372,-270.839,-134.961]','p_c1_unload = [-134.015,140.941,37.268,182.715,-271.290,-136.023]'),
     117:('p_c1_unload_down = [-133.561,140.586,38.163,182.176,-270.837,-134.961]','p_c1_unload_down = [-134.015,140.941,37.268,182.715,-271.290,-136.023]'),
     130:('p_unload_m2_wait = [51.507,126.321,64.645,170.483,-262.240,-135.484]','p_unload_m2_wait = [51.577,126.387,64.435,170.628,-262.170,-135.482]'),
     131:('p_unload_m2 = [57.266,126.106,64.997,170.375,-256.483,-135.334]','p_unload_m2 = [57.882,126.213,64.715,170.554,-255.866,-135.318]')}
for n,(o,nw) in T26.items():
    assert L[n-1].strip()==o,(n,L[n-1]); L[n-1]=nw
assert L[115].startswith('# C1UnloadDown')
L[115] = '# C1UnloadDown - [CNC36] 2026-11-26: set EQUAL to C1Unload (no separate down move; MoveL of 0 mm)'
assert L[143].startswith('# Process 8 Case 1 - Change Tool'), L[143]
L[143] = L[143] + ' - [CNC36] 2026-11-26: Load_daotool* taught with TCP Load_vuong (62.4 mm descent), unload_daotool re-taught'
def to_movl(idx,point,old_log,new_log,vel,acc,tol,note):
    assert L[idx].strip()=='movj(%s,'%point+L[idx].strip().split(',',1)[1], L[idx]
    assert L[idx-1].strip()==old_log,(idx,L[idx-1])
    ind=L[idx][:len(L[idx])-len(L[idx].lstrip())]
    L[idx-1]=ind+new_log
    L[idx:idx+1]=[ind+'# [CNC36] '+note,ind+'%s_pose = kine_forward(%s)'%(point,point),ind+'movl(%s_pose,0,%s,%s,%s)'%(point,vel,acc,tol)]
to_movl(2681,'p_load_daotool_wait','log_message(1,"P8C1 RETURN LOAD_DAOTOOL_WAIT START")','log_message(1,"P8C1 MOVEL RETURN LOAD_DAOTOOL_WAIT START")','speed_movel_fast',3500,0,'Straight 62.4 mm lift: MoveL (was MoveJ).')
assert L[2653].strip()=='movj(p_load_daotool,0,speed_movej,200,0)', L[2653]
assert L[2652].strip()=='log_message(1,"P8C1 MOVEJ LOAD_DAOTOOL START")'
ind=L[2653][:len(L[2653])-len(L[2653].lstrip())]
L[2652]=ind+'log_message(1,"P8C1 MOVEL LOAD_DAOTOOL START")'
# 1 line -> 3 lines; all later build steps reference lines < 2653, so the shift is harmless
L[2653:2654]=[ind+'# [CNC36] Straight 62.4 mm descent: MoveL (was MoveJ). Joint point -> TCP pose by kine_forward.',
              ind+'p_load_daotool_pose = kine_forward(p_load_daotool)',
              ind+'movl(p_load_daotool_pose,0,speed_movel,200,0)']
to_movl(2644,'p_unload_daotool_wait','log_message(1,"P8C1 RETURN UNLOAD_DAOTOOL_WAIT START")','log_message(1,"P8C1 MOVEL RETURN UNLOAD_DAOTOOL_WAIT START")','speed_movel_fast',3500,0,'Straight 36.2 mm lift: MoveL (was MoveJ).')
to_movl(2617,'p_unload_daotool','log_message(1,"P8C1 MOVEJ UNLOAD_DAOTOOL START")','log_message(1,"P8C1 MOVEL UNLOAD_DAOTOOL START")','speed_movel',200,0,'Straight 36.2 mm descent: MoveL (was MoveJ).')
C1N={109:('p_c1_load = [-132.924,140.231,37.879,184.079,-267.412,44.142]','p_c1_load = [-133.226,140.148,39.140,181.366,-267.073,44.109]'),
     110:('p_c1_load_wait = [-138.586,143.111,32.339,186.740,-273.070,43.926]','p_c1_load_wait = [-136.904,141.578,36.301,182.774,-270.750,44.067]'),
     111:('p_c1_load_end = [-132.738,140.167,38.001,184.021,-267.226,44.149]','p_c1_load_end = [-132.915,140.059,39.318,181.277,-266.762,44.112]')}
for n,(o,nw) in C1N.items():
    assert L[n-1].strip()==o,(n,L[n-1]); L[n-1]=nw
assert L[107].startswith('# Updated taught positions for CNC1 Load.')
L[107] = L[107] + ' - [CNC36] re-taught 2026-11-26 with TCP Load_Tron (round head)'
assert L[118].startswith('# Process 2 Case 3 - Load CNC2')
L[118] = L[118] + ' - [CNC36] 2026-11-26: LoadM2_Wait/LoadC2/EndLoadM2v1 = SQUARE head set (TCP Load_vuong)'
# sanity anchors (1-based original numbering)
assert ln(71).startswith('p_c2_user_x_offset')
assert ln(131).startswith('p_unload_m2 =')
assert ln(527).strip()=='end' and ln(528).strip().startswith('home_match_code = 0')
assert ln(643).strip().startswith('home_test_tcp = kine_forward(p_c1_load_end)')
assert ln(817).strip()=='end' and 'p_load_c2_max' in ln(816)
assert ln(842).strip().startswith('if(home_actual_joint[0] < home_match_joint_min[0])') and ln(877).strip()=='end'
assert 'at_c1_load_end == 1' in ln(1163) and ln(1311).strip()=='end'
assert ln(1918).strip()=='cnc_motion_case = 0' and ln(1951).strip()=='end' and 'P4 USE SHARED' in ln(1950)
assert 'cnc_motion_case == 29' in ln(1994) and ln(2330).strip()=='end'
assert 'set_digital_output(4,78,1,1)' in ln(2057) and 'set_digital_output(4,77,1,1)' in ln(2229)

MAP = [('p_c1_user_x_offset','p_odd_user_x_offset'),('p_c2_user_x_offset','p_even_user_x_offset'),
 ('p_air_c1v1','p_odd_air_v1'),('p_air_switch_tool','p_odd_air_switch_tool'),
 ('p_c1_load_wait','p_odd_load_wait'),('p_c1_load_end','p_odd_load_end'),('p_c1_load','p_odd_load'),
 ('p_c1_unload_wait','p_odd_unload_wait'),('p_c1_unload_down','p_odd_unload_down'),('p_c1_unload','p_odd_unload'),
 ('p_air_c2v1','p_even_air_v1'),('p_air_c2','p_even_air'),('p_load_m2_wait','p_even_load_wait'),
 ('p_load_c2','p_even_load'),('p_end_load_m2v1','p_even_load_end'),('p_unload_m2_wait','p_even_unload_wait'),
 ('p_unload_m2','p_even_unload'),('p_door_c1','p_odd_door'),('p_door_c2','p_even_door')]
cnt = {}
def remap(line):
    for a,b in MAP:
        line, n = re.subn(r'\b%s\b' % a, b, line)
        cnt[a] = cnt.get(a,0)+n
    return line
for lo,hi in [(305,440),(1605,1637)]:
    for i in range(lo-1,hi):
        L[i] = re.sub(r'\bp_door_c1\b','p_odd_door',L[i]); L[i] = re.sub(r'\bp_door_c2\b','p_even_door',L[i])
kj=0
for i in range(1100-1,1380):
    L[i],n1 = re.subn(r'(door_c1_keep_j6_joint\[(\d)\]) = -?[0-9.]+\s*$', r'\1 = p_odd_door[\2]', L[i])
    L[i],n2 = re.subn(r'(door_c2_keep_j6_joint\[(\d)\]) = -?[0-9.]+\s*$', r'\1 = p_even_door[\2]', L[i])
    kj+=n1+n2
assert kj==55, kj
for lo,hi in [(643,817),(1163,1311),(1994,2330)]:
    for i in range(lo-1,hi):
        L[i] = remap(L[i])

def sel_block(ind):
    s=' '*ind
    sets = [(1,'CNC1 CNC2',dict(od='p_door_c1',ed='p_door_c2',oo='p_c1_user_x_offset',oav='p_air_c1v1',oas='p_air_switch_tool',olw='p_c1_load_wait',ol='p_c1_load',ole='p_c1_load_end',ouw='p_c1_unload_wait',ou='p_c1_unload',oud='p_c1_unload_down',
                                   eo='p_c2_user_x_offset',eav='p_air_c2v1',ea='p_air_c2',elw='p_load_m2_wait',el='p_load_c2',ele='p_end_load_m2v1',euw='p_unload_m2_wait',eu='p_unload_m2'))]
    for pair,(o,e) in [(2,('c3','c4')),(3,('c5','c6'))]:
        sets.append((pair,'CNC%s CNC%s'%(o[1],e[1]),dict(od='p_door_%s'%o,ed='p_door_%s'%e,oo='p_%s_user_x_offset'%o,oav='p_%s_air_v1'%o,oas='p_%s_air_switch_tool'%o,olw='p_%s_load_wait'%o,ol='p_%s_load'%o,ole='p_%s_load_end'%o,ouw='p_%s_unload_wait'%o,ou='p_%s_unload'%o,oud='p_%s_unload_down'%o,
                                   eo='p_%s_user_x_offset'%e,eav='p_%s_air_v1'%e,ea='p_%s_air'%e,elw='p_%s_load_wait'%e,el='p_%s_load'%e,ele='p_%s_load_end'%e,euw='p_%s_unload_wait'%e,eu='p_%s_unload'%e)))
    names=[('od','p_odd_door'),('ed','p_even_door'),('oo','p_odd_user_x_offset'),('oav','p_odd_air_v1'),('oas','p_odd_air_switch_tool'),('olw','p_odd_load_wait'),('ol','p_odd_load'),('ole','p_odd_load_end'),('ouw','p_odd_unload_wait'),('ou','p_odd_unload'),('oud','p_odd_unload_down'),
           ('eo','p_even_user_x_offset'),('eav','p_even_air_v1'),('ea','p_even_air'),('elw','p_even_load_wait'),('el','p_even_load'),('ele','p_even_load_end'),('euw','p_even_unload_wait'),('eu','p_even_unload')]
    out=[s+'# [CNC36] Load the active CNC point set (p_odd_* / p_even_*) from cnc_pair.']
    for pair,label,d in sets:
        out.append(s+'if(cnc_pair == %d):'%pair)
        for k,n in names: out.append(s+'    %s = %s'%(n,d[k]))
        out.append(s+'    log_message(1,"ACTIVE POINT SET %s")'%label)
        out.append(s+'end')
    return out

def ai16_pair_ifs(ind, var, target='cnc_pair'):
    s=' '*ind; out=[]
    for pair,lo,hi in [(1,0.5,2.5),(2,2.5,4.5),(3,4.5,6.5)]:
        out += [s+'if(%s >= %.1f):'%(var,lo), s+'    if(%s < %.1f):'%(var,hi), s+'        %s = %d'%(target,pair), s+'    end', s+'end']
    return out

# ---- 1918-1951: case execution mapping ----
I=28; s=' '*I
case_block=[s+'cnc_motion_case = 0',
 s+'# [CNC36] P2/P3/P4 share one Case motion code (cnc_motion_case 29..32).',
 s+'# cnc_pair selects the taught point set used by that motion:',
 s+'# 1 = CNC1/CNC2 (Axis1 Pos CNC12), 2 = CNC3/CNC4 (Pos CNC34), 3 = CNC5/CNC6 (Pos CNC56).',
 s+'if(active_process == 2):', s+'    cnc_motion_case = active_case', s+'    cnc_pair = 1', s+'end']
for proc,base,pair in [(3,34,2),(4,39,3)]:
    case_block.append(s+'if(active_process == %d):'%proc)
    for k in range(4):
        case_block += [s+'    if(active_case == %d):'%(base+k), s+'        cnc_motion_case = %d'%(29+k), s+'    end']
    case_block += [s+'    cnc_pair = %d'%pair, s+'    log_message(1,"CURRENT P%d USE SHARED CNC MOTION CASE1-4")'%proc, s+'end']
case_block += [s+'if(cnc_motion_case > 0):'] + sel_block(I+4) + [
 s+'    # [CNC36] Warning only: AI16 (CNC number from PLC) should belong to the active pair.',
 s+'    # Confirm AI16 meaning with the PLC side before turning this into a blocking interlock.',
 s+'    cnc_pos_ai16 = get_analog_input(4,15)',
 s+'    cnc_pos_pair = 0'] + ai16_pair_ifs(I+4,'cnc_pos_ai16','cnc_pos_pair') + [
 s+'    cnc_pos_mismatch = 1',
 s+'    if(cnc_pos_pair == cnc_pair):',
 s+'        cnc_pos_mismatch = 0',
 s+'    end',
 s+'    if(cnc_pos_mismatch == 1):',
 s+'        log_message(2,"WARNING AI16 CNC NUMBER NOT IN ACTIVE PAIR CHECK AXIS1 POSITION")',
 s+'    end', s+'end']

# ---- 842-877: joint tolerance validation ----
I=16; s=' '*I
val=[s+'# [CNC36] Joint tolerance +/-5 deg is computed from the matched taught point itself,',
     s+'# so re-taught points and CNC3..CNC6 points need no extra *_min/*_max literal arrays.',
     s+'# Arithmetic inside if() is already used by the TCP check above on this controller.']
for j in range(6):
    val += [s+'if(home_actual_joint[%d] < home_match_joint[%d] - 5.0):'%(j,j), s+'    home_match_valid = 0', s+'end',
            s+'if(home_actual_joint[%d] > home_match_joint[%d] + 5.0):'%(j,j), s+'    home_match_valid = 0', s+'end']

# ---- after 527: home pair selection ----
home_sel=[s+'# [CNC36] Select the CNC point set for Home recognition from AI16.',
          s+'# AI16 1/2 -> CNC1/2 set, 3/4 -> CNC3/4 set, 5/6 -> CNC5/6 set.',
          s+'# If AI16 is outside 0.5..6.5, keep the set of the last executed Case.'] + ai16_pair_ifs(I,'ai16_home_cnc') + sel_block(I)

# ---- chuck comments ----
chuck1=' '*44+'# [CNC36] DO79/DI79 = Clamp Chuck of the odd CNC, shared by P2/P3/P4 (confirmed 2026-11):'
chuck1b=' '*44+'# the PLC clamps CNC1, CNC3 or CNC5 according to the active Process.'
chuck2=' '*48+'# [CNC36] DO78/DI78 = Clamp Chuck of the even CNC, shared by P2/P3/P4 (confirmed 2026-11):'
chuck2b=' '*48+'# the PLC clamps CNC2, CNC4 or CNC6 according to the active Process.'

# ---- header inserts ----
def copy_of(name):
    for x in L[:200]:
        m=re.match(r'^%s\s*=\s*(\[.*\])\s*$'%re.escape(name),x)
        if m: return m.group(1)
    raise Exception(name)
off=['# [CNC36] CNC3..CNC6 fine offsets in the active User frame (same meaning as CNC1/CNC2).',
 'p_c3_user_x_offset = [0.0,0,0.0,0,0,0]','p_c4_user_x_offset = [0.0,0,0.0,0,0,0]',
 'p_c5_user_x_offset = [0.0,0,0.0,0,0,0]','p_c6_user_x_offset = [0.0,0,0.0,0,0,0]']
pts=['','# ===== [CNC36] SPARE: CNC2 load points for the ROUND head (TCP Load_Tron), taught 2026-11-26 =====',
 '# Not used now (CNC2 is loaded with the square head). Kept for a future product/model selection.',
 'p_c2_tron_load_wait = [51.981,126.155,66.601,166.126,-261.765,44.318]','p_c2_tron_load = [57.453,126.223,66.572,166.066,-256.294,44.208]','p_c2_tron_load_end = [57.814,126.257,66.520,166.082,-255.933,44.201]',
 '# ===== [CNC36] CNC3..CNC6 TAUGHT POINTS =====',
 '# The robot base rides on Axis1 (moved by PLC): Pos1 = CNC1/2, Pos2 = CNC3/4, Pos3 = CNC5/6.',
 '# Joint points are relative to the robot base. If Axis1 stops at exactly the same relative',
 '# position in front of every pair, the CNC1/CNC2 values could be reused unchanged.',
 '# !!! PLACEHOLDER: every value below is a COPY of CNC1 (odd side) or CNC2 (even side). !!!',
 '# !!! Re-teach / verify each point on the real machine before running at normal speed. !!!']
odd=[('air_v1','p_air_c1v1'),('air_switch_tool','p_air_switch_tool'),('load_wait','p_c1_load_wait'),('load','p_c1_load'),('load_end','p_c1_load_end'),('unload_wait','p_c1_unload_wait'),('unload','p_c1_unload'),('unload_down','p_c1_unload_down')]
even=[('air_v1','p_air_c2v1'),('air','p_air_c2'),('load_wait','p_load_m2_wait'),('load','p_load_c2'),('load_end','p_end_load_m2v1'),('unload_wait','p_unload_m2_wait'),('unload','p_unload_m2')]
pts += ['# Door points (robot posture in the aisle in front of each CNC pair) - PLACEHOLDER',
        '# DoorC3/DoorC5 copy DoorC1 (odd side), DoorC4/DoorC6 copy DoorC2 (even side).']
for c,ref in [('c3','p_door_c1'),('c4','p_door_c2'),('c5','p_door_c1'),('c6','p_door_c2')]:
    pts += ['# copy of %s'%ref, 'p_door_%s = %s'%(c,copy_of(ref))]
pts.append('')
for c,lst,side in [('c3',odd,'P3 Case1/Case2, odd side like CNC1'),('c4',even,'P3 Case3/Case4, even side like CNC2'),('c5',odd,'P4 Case1/Case2, odd side like CNC1'),('c6',even,'P4 Case3/Case4, even side like CNC2')]:
    pts.append('# CNC%s (%s) - PLACEHOLDER'%(c[1],side))
    for suf,ref in lst: pts += ['# copy of %s'%ref, 'p_%s_%s = %s'%(c,suf,copy_of(ref))]
    pts.append('')
pts += ['# ===== [CNC36] ACTIVE CNC POINT SET =====',
 '# Case motion (cnc_motion_case 29..32) and DI90 Home recovery use only p_odd_* / p_even_*.',
 '# They are reloaded from cnc_pair at every P2/P3/P4 Case and at every DI90 Home request.',
 'cnc_pair = 1','cnc_pos_ai16 = 0','cnc_pos_pair = 0','cnc_pos_mismatch = 0']
pts += sel_block(0)
pts = [x for x in pts if 'log_message' not in x or not x.startswith('    log')]  # no log at init
pts.append('')

# assemble (bottom-up so numbering stays valid)
def rep(lo,hi,new): L[lo-1:hi] = new
L.insert(2229-1, chuck2b); L.insert(2229-1, chuck2)
L.insert(2057-1, chuck1b); L.insert(2057-1, chuck1)
rep(1918,1951,case_block)
I2=16; s2=' '*I2
entry=[s2+'# [CNC36] Select the CNC pair and its point set (incl. Door) before the entry Door move.']
for proc,pair in [(2,1),(3,2),(4,3)]:
    entry += [s2+'if(active_process == %d):'%proc, s2+'    cnc_pair = %d'%pair, s2+'end']
entry += [s2+'if(door_select == 0):'] + sel_block(I2+4) + [s2+'end']
assert ln(1605).strip()=='if(door_select == 0):'
L[1605-1:1605-1] = entry
rep(842,877,val)
# remove min/max assignments in 740-817
for i in range(817-1,740-2,-1):
    if re.search(r'home_match_joint_(min|max) =',L[i]): del L[i]
L[528-1:528-1] = home_sel
L[132-1:132-1] = pts
L[72-1:72-1] = off
hdr=['# [CNC36] 2026-11: extended for CNC3..CNC6 (P3 = CNC3/CNC4, P4 = CNC5/CNC6).',
 '#   Search "[CNC36]" for every change. Motion code is shared; only the point set changes.',
 '#   CNC3..CNC6 points (incl. Door) are PLACEHOLDER copies of CNC1/CNC2 and must be re-taught.',
 '#   Home keep-J6 Door moves read J1..J5 from p_odd_door/p_even_door (verify on first load).',
 '#']
L[0:0]=hdr
def danger_retreat(side):
    # side: ('C1','DOORC1','odd','p_odd_air_v1','C1LOADWAIT','C1UNLOADWAIT','AIRC1V1','at_c1_load_wait','at_c1_unload_wait',hint)
    tag,door,pre,airv1,lw,uw,airname,flag_lw,flag_uw,hint=side
    i0=[i for i,l in enumerate(L) if 'log_message(2,"HOME CNC%s DANGER SIDE DETECTED AFTER POINT CHECK")'%tag[1] in l]
    assert len(i0)==1; i0=i0[0]
    i1=[i for i in range(i0,i0+40) if 'log_message(1,"HOME ROUTE %s COMPLETE")'%door in L[i]][0]
    old=L[i0+1:i1+1]
    s=' '*24
    var='home_%s_wait_route'%tag.lower()
    new=[s+'# [CNC36] Danger side: retreat by MoveL to the Wait point of the tool facing the chuck,',
     s+'# then to the Door. Tool identified by J6 (Load ~ +44, Air ~ -45, Unload ~ -135);',
     s+'# thresholds are midpoints of the active taught J6 values. Speed 30 mm/s.',
     s+'%s = 0'%var,
     s+'if(home_actual_joint[5] >= (p_%s_load_wait[5] + %s[5]) * 0.5):'%(pre,airv1),
     s+'    %s = 1'%var, s+'end',
     s+'if(home_actual_joint[5] <= (p_%s_unload_wait[5] + %s[5]) * 0.5):'%(pre,airv1),
     s+'    %s = 2'%var, s+'end',
     s+'if(%s == 1):'%var,
     s+'    log_message(1,"HOME CNC%s DANGER LOAD TOOL MOVEL %s START")'%(tag[1],lw),
     s+'    home_wait_pose = kine_forward(p_%s_load_wait)'%pre,
     s+'    home_wait_pose = pose_add(home_wait_pose,p_%s_user_x_offset)'%pre,
     s+'    movl(home_wait_pose,0,30,200,0)',
     s+'    %s = 1'%flag_lw, s+'    home_route_hint = %d'%hint,
     s+'    log_message(1,"HOME ROUTE %s COMPLETE")'%lw, s+'end',
     s+'if(%s == 2):'%var,
     s+'    log_message(1,"HOME CNC%s DANGER UNLOAD TOOL MOVEL %s START")'%(tag[1],uw),
     s+'    home_wait_pose = kine_forward(p_%s_unload_wait)'%pre,
     s+'    movl(home_wait_pose,0,30,200,0)',
     s+'    %s = 1'%flag_uw, s+'    home_route_hint = %d'%hint,
     s+'    log_message(1,"HOME ROUTE %s COMPLETE")'%uw, s+'end',
     s+'# Air-blow orientation: back to the air entry point (the air Wait), then straight to the Door.',
     s+'if(%s == 0):'%var,
     s+'    log_message(1,"HOME CNC%s DANGER AIR TOOL MOVEL %s START")'%(tag[1],airname),
     s+'    home_wait_pose = kine_forward(%s)'%airv1,
     s+'    movl(home_wait_pose,0,30,200,0)',
     s+'    log_message(1,"HOME ROUTE %s COMPLETE")'%airname]+['    '+x if x.strip() else x for x in old]+[s+'end']
    L[i0+1:i1+1]=new
danger_retreat(('C1','DOORC1','odd','p_odd_air_v1','C1LOADWAIT','C1UNLOADWAIT','AIRC1V1','at_c1_load_wait','at_c1_unload_wait',1))
danger_retreat(('C2','DOORC2','even','p_even_air_v1','LOADM2_WAIT','UNLOADM2_WAIT','AIRC2V1','at_load_m2_wait','at_unload_m2_wait',2))
# recognized AIRC2: go back to AirC2v1 (air entry point) before DoorC2
i=[k for k,l in enumerate(L) if l.strip()=='log_message(1,"HOME ROUTE CURRENT AT AIRC2")']
assert len(i)==1; i=i[0]
ind=L[i][:len(L[i])-len(L[i].lstrip())]
L[i+1:i+1]=[ind+'# [CNC36] Retreat AirC2 -> AirC2v1 (reverse of the entry path) before DoorC2.',
            ind+'log_message(1,"HOME ROUTE MOVEL AIRC2V1 START")',
            ind+'home_wait_pose = kine_forward(p_even_air_v1)',
            ind+'movl(home_wait_pose,0,30,200,0)',
            ind+'log_message(1,"HOME ROUTE AIRC2V1 COMPLETE")']
open(dst,'w',newline='').write('\r\n'.join(L))
print({k:v for k,v in cnt.items()})
