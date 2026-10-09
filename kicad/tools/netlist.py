"""AC-30 netlist, transcribed from docs/ac30_schematica.jpg (switching section),
docs/ac30_wiring1a.jpg (J1-J5 board connector signal order) and docs/AC30-BOM.md.

Each part: (ref, lib_id, value, {unit: {pin: net}}, group)
A pin mapped to None gets a no-connect flag. Pins left out of a unit get a
no-connect flag too, except on sheet "moddemod" where parts are unwired.
"""

P5, G = '+5V', 'GND'

# Footprints for parts that sit on the PC board.  Front-panel parts get none.
FP = {
    'R': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    'RT': 'Potentiometer_THT:Potentiometer_Bourns_3386P_Vertical',
    'C': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    'CP': 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
    'CPL': 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm',
    'D': 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal',
    'DR': 'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal',
    'Q': 'Package_TO_SOT_THT:TO-92_Inline',
    'DIP8': 'Package_DIP:DIP-8_W7.62mm',
    'DIP14': 'Package_DIP:DIP-14_W7.62mm',
    'DIP16': 'Package_DIP:DIP-16_W7.62mm',
    'REG': 'Package_TO_SOT_THT:TO-220-3_Vertical',
    'RLY': 'Relay_THT:Relay_SPST_StandexMeder_SIL_Form1A',
    'LED': 'LED_THT:LED_D5.0mm',
}

parts = []


def add(ref, lib, value, units, group, fp=None, sheet='main'):
    parts.append(dict(ref=ref, lib=lib, value=value, units=units, group=group, fp=fp, sheet=sheet))


def R(ref, value, a, b, group, sheet='main'):
    add(ref, 'Device:R', value, {1: {'1': a, '2': b}}, group, FP['R'], sheet)


def C(ref, value, a, b, group, sheet='main'):
    add(ref, 'Device:C', value, {1: {'1': a, '2': b}}, group, FP['C'], sheet)


def CP(ref, value, pos, neg, group, fp='CP', sheet='main'):
    add(ref, 'Device:C_Polarized', value, {1: {'1': pos, '2': neg}}, group, FP[fp], sheet)


def D(ref, lib, value, k, a, group, fp='D', sheet='main'):
    add(ref, lib, value, {1: {'1': k, '2': a}}, group, FP[fp] if fp else None, sheet)


def Q(ref, pnp, e, b, c, group):
    lib = 'Transistor_BJT:Q_PNP_EBC' if pnp else 'Transistor_BJT:Q_NPN_EBC'
    add(ref, lib, '2N5087' if pnp else '2N5210', {1: {'1': e, '2': b, '3': c}}, group, FP['Q'])


# --------------------------------------------------------------------------
# Board connectors: pin positions match the original board artwork
# (docs/ac30_redblue150.jpg), pin 1 at the left seen from the component side;
# None = unused position.
# --------------------------------------------------------------------------
GRP = 'Board connectors (pin positions per original artwork)'

def conn(ref, value, nets, group=GRP):
    n = len(nets)
    add(ref, f'Connector_Generic:Conn_01x{n:02d}', value,
        {1: {str(i + 1): net for i, net in enumerate(nets)}}, group,
        f'Connector_Molex:Molex_KK-396_A-41791-{n:04d}_1x{n:02d}_P3.96mm_Vertical')

conn('J1', 'Front panel harness 1', ['MOTOR_1A', P5, 'LED_READ_DATA', G, 'RELAY_1', 'LED_REC_DATA',
                                     'MOTOR_1B', 'LOCAL_REMOTE', 'READ_RST', 'REC_RLY_DRV', 'MAN_MOTOR',
                                     'READ_RLY_DRV', 'RELAY_2', 'MOTOR_2A', None])
conn('J2', 'Front panel harness 2', ['MOTOR_2B', 'READ_SET', 'REC_SET', 'REC_RST', 'LED_READ_RDY',
                                     'LED_REC_RDY', 'AUDIO_OUT', 'AUDIO_IN', 'CARRIER_EN_N', G,
                                     '18VAC_A', '18VAC_B'])
conn('J3', 'Computer interface (COMP)', [G, 'CPU_CLK_OUT', 'CPU_CLK_IN', None, 'CPU_RS232_IN',
                                         'CPU_RS232_OUT', None, None, None, None])
conn('J4', 'Control interface', [None, G, None, 'LOCAL_REMOTE', 'STOP_RECORD', P5, 'STOP_READ',
                                 'CTRL_INVERT', 'START_READ', 'START_RECORD', 'TERM_CLK_OUT',
                                 'TERM_CLK_IN', 'CARRIER_DETECT', 'CARRIER_EN_N', None])
conn('J5', 'Terminal interface (TERM)', [G, None, None, None, 'TERM_RS232_OUT', 'TERM_RS232_IN',
                                         None, None, None, None])

# --------------------------------------------------------------------------
# RS-232 level conversion and clock input clamps
# --------------------------------------------------------------------------
GRP = 'RS-232 receivers / drivers, clock clamps'
add('IC12', 'AC30:MC1489', '1489', {
    1: {'1': 'CPU_RS232_OUT', '2': None, '3': 'CPU_DATA'},       # drawing IC12A
    2: {'4': 'TERM_RS232_OUT', '5': None, '6': 'TERM_DATA'},     # drawing IC12B
    3: {'10': None, '9': None, '8': None},
    4: {'13': None, '12': None, '11': None},
    5: {'14': P5, '7': G}}, GRP, FP['DIP14'])
add('IC15', 'AC30:MC1488', '1488', {
    1: {'2': None, '3': None},
    2: {'4': None, '5': None, '6': None},
    3: {'9': 'TERM_ECHO', '10': 'TERM_TX_SEL', '8': 'TERM_RS232_IN'},  # drawing IC15A
    4: {'12': 'CPU_RX', '13': P5, '11': 'CPU_RS232_IN'},              # drawing IC15B
    5: {'14': 'V_RS232+', '1': 'V_RS232-', '7': G}}, GRP, FP['DIP14'])
C('C19', '470pF', 'TERM_RS232_IN', G, GRP)
C('C20', '470pF', 'CPU_RS232_IN', G, GRP)
D('D8', 'Diode:1N4148', '1N4148', P5, 'CPU_CLK_OUT', GRP)
D('D9', 'Diode:1N4148', '1N4148', 'CPU_CLK_OUT', G, GRP)
D('D10', 'Diode:1N4148', '1N4148', P5, 'TERM_CLK_OUT', GRP)
D('D11', 'Diode:1N4148', '1N4148', 'TERM_CLK_OUT', G, GRP)

# --------------------------------------------------------------------------
# Local / remote steering logic and data selectors
# --------------------------------------------------------------------------
GRP = 'Local/Remote steering and data/clock selectors'
R('R41', '10K', P5, 'LOCAL_REMOTE', GRP)
add('IC11', '4xxx:4001', '4001', {
    1: {'1': 'REMOTE_N', '2': 'READ_ACTIVE_N', '3': 'SEL_TERM_CLK'},   # IC11A
    2: {'5': 'READ_ACTIVE_N', '6': 'LOCAL_REMOTE', '4': 'SEL_CPU_CLK'},  # IC11B
    3: {'8': 'TERM_DATA_N', '9': 'TAPE_DATA', '10': 'ECHO_N'},          # IC11C
    4: {'12': 'ECHO_N', '13': 'LOCAL_REMOTE', '11': 'CPU_RX_N'},        # IC11D
    5: {'14': P5, '7': G}}, GRP, FP['DIP14'])
add('IC7', '4xxx:4049', '4049', {
    1: {'3': 'CPU_RX_N', '2': 'CPU_RX'},              # IC7A
    2: {'5': 'TAPE_DATA_N', '4': 'TAPE_DATA'},        # IC7B
    3: {'7': 'REC_DATA_N', '6': 'DATA_IN'},           # IC7C
    4: {'9': 'TERM_DATA', '10': 'TERM_DATA_N'},       # IC7D (drawing labels it 8->9)
    5: {'11': 'LOCAL_REMOTE', '12': 'REMOTE_N'},      # IC7E
    6: {'14': 'DATA_SEL', '15': 'DATA_SEL_N'},        # IC7F
    7: {'1': P5, '8': G}}, GRP, FP['DIP16'])
# 4053 sections (drawing name: X input, Y input, common, select):
#   IC6A: 2, 1, 15, 10   IC6B: 5, 3, 4, 9   IC6C: 12, 13, 14, 11
add('IC6', '4xxx:4053', '4053', {1: {
    '2': 'CPU_CLK_OUT', '1': 'CLOCK_OUT', '15': 'CPU_CLK_IN', '10': 'SEL_CPU_CLK',
    '5': 'CPU_CLK_OUT', '3': 'TERM_CLK_OUT', '4': 'CLOCK_IN', '9': 'LOCAL_REMOTE',
    '12': 'CPU_DATA', '13': 'TERM_DATA', '14': 'DATA_SEL', '11': 'LOCAL_REMOTE',
    '6': G, '7': G, '8': G, '16': P5}}, GRP, FP['DIP16'])
#   IC14A: 2, 1, 15, 10  IC14B: 5, 3, 4, 9  IC14C: 12, 13, 14, 11
add('IC14', '4xxx:4053', '4053', {1: {
    '2': P5, '1': 'TERM_DATA', '15': 'TERM_ECHO', '10': 'LOCAL_REMOTE',
    '5': 'TERM_CLK_OUT', '3': 'CLOCK_OUT', '4': 'TERM_CLK_IN', '9': 'SEL_TERM_CLK',
    '12': 'CPU_DATA', '13': 'TAPE_DATA_N', '14': 'TERM_TX_SEL', '11': 'LOCAL_REMOTE',
    '6': G, '7': G, '8': G, '16': P5}}, GRP, FP['DIP16'])
add('IC9', '4xxx:4023', '4023', {
    1: {'1': 'READ_EN', '8': P5, '2': 'CARRIER_DETECT', '9': 'READ_ACTIVE_N'},   # IC9A
    2: {'5': 'READ_EN', '3': 'DATA_OUT', '4': 'CARRIER_DETECT', '6': 'TAPE_DATA_N'},  # IC9B
    3: {'12': 'REC_EN', '13': P5, '11': 'DATA_SEL_N', '10': 'REC_DATA_N'},      # IC9C
    4: {'14': P5, '7': G}}, GRP, FP['DIP14'])

# --------------------------------------------------------------------------
# Record / read control latches
# --------------------------------------------------------------------------
GRP = 'Record / read control latches and power-on reset'
R('R42', '10K', P5, 'CTRL_INVERT', GRP)
R('R44', '10K', P5, 'START_RECORD', GRP)
R('R45', '10K', P5, 'START_READ', GRP)
R('R46', '10K', P5, 'STOP_RECORD', GRP)
R('R47', '10K', P5, 'STOP_READ', GRP)
add('IC13', '4xxx:4070', '4070', {
    1: {'1': 'STOP_RECORD', '2': 'CTRL_INVERT', '3': 'STOP_REC_P'},    # IC13A
    2: {'5': 'CTRL_INVERT', '6': 'START_RECORD', '4': 'START_REC_P'},  # IC13B
    3: {'9': 'CTRL_INVERT', '8': 'START_READ', '10': 'START_READ_P'},  # IC13C (drawing: 7,8)
    4: {'12': 'CTRL_INVERT', '13': 'STOP_READ', '11': 'STOP_READ_P'},  # IC13D
    5: {'14': P5, '7': G}}, GRP, FP['DIP14'])
C('C12', '1000pF', 'START_READ_P', 'READ_SET', GRP)
C('C13', '1000pF', 'START_REC_P', 'REC_SET', GRP)
C('C14', '1000pF', 'STOP_READ_P', 'READ_RST', GRP)
C('C15', '1000pF', 'STOP_REC_P', 'REC_RST', GRP)
add('IC8', '4xxx:4013', '4013', {
    1: {'6': 'READ_SET', '4': 'READ_RST', '5': G, '3': G, '1': 'READ_EN', '2': 'READ_EN_N'},   # read latch
    2: {'8': 'REC_SET', '10': 'REC_RST', '9': G, '11': G, '13': 'REC_EN', '12': 'REC_EN_N'},  # record latch
    3: {'14': P5, '7': G}}, GRP, FP['DIP14'])
R('R23', '100K', 'READ_SET', G, GRP)
R('R24', '100K', 'REC_SET', G, GRP)
R('R25', '100K', 'READ_RST', 'POR', GRP)
R('R26', '100K', 'REC_RST', 'POR', GRP)
CP('C16', '100uF 16V', P5, 'POR', GRP, 'CPL')
D('D5', 'Diode:1N4148', '1N4148', 'POR', G, GRP)
R('R27', '10K', 'POR', G, GRP)

# --------------------------------------------------------------------------
# Indicators and drivers
# --------------------------------------------------------------------------
GRP = 'LED drivers, relay drivers, carrier-enable delay'
R('R28', '10K', 'REC_EN', 'Q5_B', GRP)
Q('Q5', False, G, 'Q5_B', 'Q5_C', GRP)
R('R30', '470', 'Q5_C', 'LED_REC_RDY', GRP)
R('R29', '10K', 'READ_EN', 'Q6_B', GRP)
Q('Q6', False, G, 'Q6_B', 'Q6_C', GRP)
R('R31', '470', 'Q6_C', 'LED_READ_RDY', GRP)
R('R34', '10K', 'DATA_IN', 'Q8_B', GRP)
Q('Q8', False, G, 'Q8_B', 'Q8_C', GRP)
R('R35', '470', 'Q8_C', 'LED_REC_DATA', GRP)
R('R36', '10K', 'TAPE_DATA', 'Q7_B', GRP)
Q('Q7', False, G, 'Q7_B', 'Q7_C', GRP)
R('R37', '470', 'Q7_C', 'LED_READ_DATA', GRP)
R('R32', '10K', 'REC_EN_N', 'Q9_B', GRP)
Q('Q9', True, P5, 'Q9_B', 'REC_RLY_DRV', GRP)
R('R33', '10K', 'READ_EN_N', 'Q10_B', GRP)
Q('Q10', True, P5, 'Q10_B', 'READ_RLY_DRV', GRP)
D('D6', 'Diode:1N4148', '1N4148', 'RELAY_1', 'MAN_MOTOR', GRP)
D('D7', 'Diode:1N4148', '1N4148', 'RELAY_2', 'MAN_MOTOR', GRP)
# Standex-Meder SIL reed relay: coil 5-3, contact 7-1
add('RLY1', 'Relay:SILxx-1Axx-71x', '6V reed relay',
    {1: {'5': 'RELAY_1', '3': G, '7': 'MOTOR_1A', '1': 'MOTOR_1B'}}, GRP, FP['RLY'])
add('RLY2', 'Relay:SILxx-1Axx-71x', '6V reed relay',
    {1: {'5': 'RELAY_2', '3': G, '7': 'MOTOR_2A', '1': 'MOTOR_2B'}}, GRP, FP['RLY'])
add('IC10', 'Timer:NE555P', '555', {1: {
    '2': 'REC_EN', '3': 'DELAY_OUT', '4': P5, '5': 'IC10_CV', '6': 'DELAY_RC', '7': 'DELAY_RC'},
    0: {'1': G, '8': P5}}, GRP, FP['DIP8'])
R('R38', '47K', P5, 'DELAY_RC', GRP)
CP('C17', '10uF 10V tant', 'DELAY_RC', G, GRP)
Q('Q11', True, 'DELAY_RC', 'REC_EN', G, GRP)
C('C18', '0.01uF', 'IC10_CV', G, GRP)
R('R43', '470', 'DELAY_OUT', 'D18_K', GRP)
D('D18', 'Device:LED', 'LED', 'D18_K', P5, GRP, 'LED')
R('R40', '10K', 'DELAY_OUT', 'CARRIER_EN_N', GRP)

# --------------------------------------------------------------------------
# Front panel (wired to the board through J1/J2)
# --------------------------------------------------------------------------
GRP = 'Front panel switches, LEDs and jacks'
# S1 MOTOR CONTROL AUTO/MAN: in MAN, pole 1 grounds CARRIER ENABLE, pole 2 feeds +5 to MAN_MOTOR
add('S1', 'Switch:SW_DPDT_x2', 'AUTO/MAN', {
    1: {'2': 'CARRIER_EN_N', '1': G, '3': None},
    2: {'5': 'MAN_MOTOR', '4': P5, '6': None}}, GRP)
add('S2', 'Switch:SW_DPDT_x2', 'RECORD A/B', {
    1: {'2': 'AUDIO_OUT', '1': 'MIC_A', '3': 'MIC_B'},
    2: {'5': 'REC_RLY_DRV', '4': 'RELAY_1', '6': 'RELAY_2'}}, GRP)
add('S3', 'Switch:SW_DPDT_x2', 'PLAY A/B', {
    1: {'2': 'READ_RLY_DRV', '1': 'RELAY_1', '3': 'RELAY_2'},
    2: {'5': 'AUDIO_IN', '4': 'EAR_A', '6': 'EAR_B'}}, GRP)
add('S4', 'Switch:SW_SPDT_MSM', 'RECORD ON/OFF', {1: {'2': P5, '1': 'REC_SET', '3': 'REC_RST'}}, GRP)
add('S5', 'Switch:SW_SPDT_MSM', 'READER ON/OFF', {1: {'2': P5, '1': 'READ_SET', '3': 'READ_RST'}}, GRP)
add('S7', 'Switch:SW_SPDT', 'LOCAL/REMOTE', {1: {'2': 'LOCAL_REMOTE', '1': G, '3': None}}, GRP)
D('D19', 'Device:LED', 'RECORD RDY', 'LED_REC_RDY', P5, GRP, None)
D('D20', 'Device:LED', 'READ RDY', 'LED_READ_RDY', P5, GRP, None)
D('D21', 'Device:LED', 'REC DATA', 'LED_REC_DATA', P5, GRP, None)
D('D22', 'Device:LED', 'READ DATA', 'LED_READ_DATA', P5, GRP, None)
for ref, val, tip, sl in (('J6', 'MIC A', 'MIC_A', G), ('J7', 'MIC B', 'MIC_B', G),
                          ('J8', 'EAR A', 'EAR_A', G), ('J9', 'EAR B', 'EAR_B', G),
                          ('J10', 'MOTOR A', 'MOTOR_1A', 'MOTOR_1B'),
                          ('J11', 'MOTOR B', 'MOTOR_2A', 'MOTOR_2B')):
    add(ref, 'Connector_Audio:AudioJack2', val, {1: {'T': tip, 'S': sl}}, GRP)

# --------------------------------------------------------------------------
# Modulator / demodulator and power supply BOM parts.  No schematic for these
# is in docs/, so they are NOT placed (sheet 'omitted'); the board brings the
# interface nets out to solder pads instead (see below).  Change S back to
# 'moddemod' to place them once the circuit is known.
# --------------------------------------------------------------------------
S = 'omitted'
GRP = 'Mod/demod and power supply parts (BOM only - NOT WIRED, schematic not available)'
add('IC1', '4xxx:4013', '4013', {1: {}, 2: {}, 3: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
add('IC5', '4xxx:4013', '4013', {1: {}, 2: {}, 3: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
add('IC2', '4xxx:4001', '4001', {1: {}, 2: {}, 3: {}, 4: {}, 5: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
add('IC3', '4xxx:4070', '4070', {1: {}, 2: {}, 3: {}, 4: {}, 5: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
add('IC4', 'Amplifier_Operational:RC4558', '4558', {1: {}, 2: {}, 3: {}}, GRP, FP['DIP8'], S)
add('IC16', 'Regulator_Linear:L7805', '7805', {1: {'1': 'VRAW', '2': G, '3': P5}}, GRP, FP['REG'], S)
for r, v in (('R1', '33K'), ('R2', '10K'), ('R3', '10K'), ('R4', '330'), ('R5', '2.2K'), ('R6', '4.7K'),
             ('R7', '470'), ('R8', '100K'), ('R9', '10K'), ('R10', '330K'), ('R11', '10K'), ('R12', '10K'),
             ('R13', '22K'), ('R14', '22K'), ('R15', '10K'), ('R17', '100K'), ('R18', '100K'),
             ('R19', '10K'), ('R20', '10K'), ('R21', '10K'), ('R22', '10K'), ('R48', '330'), ('R49', '330')):
    add(r, 'Device:R', v, {1: {}}, GRP, FP['R'], S)
for r, v in (('R16', '20K trim'), ('R39', '200K trim')):
    add(r, 'Device:R_Potentiometer_Trim', v, {1: {}}, GRP, FP['RT'], S)
for c, v in (('C1', '1000pF'), ('C2', '2000pF'), ('C3', '0.022uF'), ('C5', '0.01uF'), ('C6', '1000pF'),
             ('C7', '0.047uF'), ('C8', '0.022uF'), ('C9', '0.047uF'), ('C10', '2700pF'), ('C11', '470pF'),
             ('C23', '0.1uF'), ('C24', '0.1uF'), ('C25', '0.1uF')):
    add(c, 'Device:C', v, {1: {}}, GRP, FP['C'], S)
add('C4', 'Device:C_Polarized', '1uF 15V', {1: {}}, GRP, FP['CP'], S)
add('C21', 'Device:C_Polarized', '1000uF 25V', {1: {}}, GRP, FP['CPL'], S)
add('C22', 'Device:C_Polarized', '100uF 16V', {1: {}}, GRP, FP['CPL'], S)
for d in ('D1', 'D2', 'D4'):
    add(d, 'Diode:1N4148', '1N4148', {1: {}}, GRP, FP['D'], S)
add('D3', 'Device:D_Zener', '1N4732 4.7V', {1: {}}, GRP, FP['D'], S)
add('D12', 'Device:D_Zener', '1N4737 7.5V', {1: {}}, GRP, FP['D'], S)
add('D13', 'Device:D_Zener', '1N4737 7.5V', {1: {}}, GRP, FP['D'], S)
for d in ('D14', 'D15', 'D16', 'D17'):
    add(d, 'Diode:1N4003', '1N4003', {1: {}}, GRP, FP['DR'], S)
for q in ('Q1', 'Q2', 'Q4'):
    add(q, 'Transistor_BJT:Q_NPN_EBC', '2N5210', {1: {}}, GRP, FP['Q'], S)
add('Q3', 'Transistor_BJT:Q_PNP_EBC', '2N5087', {1: {}}, GRP, FP['Q'], S)
add('T1', 'Device:Transformer_1P_1S', '120/240V : 18VAC 300mA', {1: {}}, GRP, None, S)
add('F1', 'Device:Fuse', '1A', {1: {}}, GRP, None, S)
add('S6', 'Switch:SW_SPDT', 'SPDT (function not shown)', {1: {}}, GRP, None, S)

# --------------------------------------------------------------------------
# Solder pads for the off-board (not yet drawn) mod/demod and power supply
# --------------------------------------------------------------------------
PAD_FP = 'Connector_Wire:SolderWire-0.5sqmm_1x01_D0.9mm_OD2.1mm'
GRP = 'Mod/demod interface pads'
for i, (net, desc) in enumerate((
        ('DATA_IN', 'DATA IN (to modulator)'),
        ('CLOCK_IN', '16X CLOCK IN (to modulator)'),
        ('CARRIER_EN_N', '~{CARRIER ENABLE} (to modulator)'),
        ('AUDIO_OUT', 'AUDIO OUT (from modulator)'),
        ('AUDIO_IN', 'AUDIO IN (to demodulator)'),
        ('DATA_OUT', 'DATA OUT (from demodulator)'),
        ('CLOCK_OUT', '16X CLOCK OUT (from demodulator)'),
        ('CARRIER_DETECT', 'CARRIER DETECT (from demodulator)'),
        (G, 'GND (mod/demod)')), 1):
    add(f'TP{i}', 'Connector:TestPoint', desc, {1: {'1': net}}, GRP, PAD_FP, 'moddemod')
GRP = 'Power supply pads'
for i, (net, desc) in enumerate((
        ('18VAC_A', '18 VAC A (from J2 / T1)'),
        ('18VAC_B', '18 VAC B (from J2 / T1)'),
        (P5, '+5V (regulated)'),
        (G, 'GND (power)'),
        ('V_RS232+', 'RS-232 V+ (IC15 pin 14)'),
        ('V_RS232-', 'RS-232 V- (IC15 pin 1)')), 10):
    add(f'TP{i}', 'Connector:TestPoint', desc, {1: {'1': net}}, GRP, PAD_FP, 'moddemod')

# Corner mounting holes, 1/4" (6.35 mm) in from each edge as on the original artwork
# (docs/ac30_redblue150.jpg); 3.2 mm unplated, for #4 or M3 screws. tools/pcb.py
# places them at the board corners.
GRP = 'Mounting holes'
for i in range(1, 5):
    add(f'H{i}', 'Mechanical:MountingHole', 'MountingHole', {1: {}}, GRP,
        'MountingHole:MountingHole_3.2mm_M3', 'moddemod')

# Nets that cross between the two sheets (drawn as global labels).
GLOBAL = {'DATA_IN': 'input', 'DATA_OUT': 'output', 'CLOCK_IN': 'input', 'CLOCK_OUT': 'output',
          'CARRIER_DETECT': 'output', 'AUDIO_OUT': 'output', 'AUDIO_IN': 'input',
          'CARRIER_EN_N': 'input', '18VAC_A': 'passive', '18VAC_B': 'passive',
          'V_RS232+': 'passive', 'V_RS232-': 'passive', 'VRAW': 'passive'}
POWER = {P5: 'power:+5V', G: 'power:GND'}
