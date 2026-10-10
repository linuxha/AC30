"""AC-30 netlist, transcribed from docs/ac30_schematica.jpg (switching section),
docs/ac30_mod_demod.pdf (modulator/demodulator), docs/ac30_PS.pdf (power supply,
built external to the board), docs/ac30_redblue150.jpg (J1-J5
board connector pin positions) and docs/AC30-BOM.md.

Each part: (ref, lib_id, value, {unit: {pin: net}}, group)
A pin mapped to None gets a no-connect flag. Pins left out of a unit get a
no-connect flag too, except on sheet "moddemod" where parts are unwired.
"""

import os

P5, G = '+5V', 'GND'

# AC30_VARIANT=smt builds the surface-mount version (kicad-smt/AC30_SMT): every
# on-board part is SMT except the Molex KK-396 connectors, the front-panel jumper pads
# and the mounting holes.
VARIANT = os.environ.get('AC30_VARIANT', 'tht')
SMT = VARIANT == 'smt'

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
if SMT:
    FP.update({
        'R': 'Resistor_SMD:R_0805_2012Metric',
        'RT': 'Potentiometer_SMD:Potentiometer_Bourns_3314G_Vertical',
        'C': 'Capacitor_SMD:C_0805_2012Metric',
        'CP': 'Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A',
        'CPL': 'Capacitor_SMD:CP_Elec_6.3x7.7',
        'D': 'Diode_SMD:D_SOD-123',
        'Q': 'Package_TO_SOT_SMD:SOT-23',
        'DIP8': 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
        'DIP14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
        'DIP16': 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
        'RLY': 'Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y',
        'LED': 'LED_SMD:LED_1206_3216Metric',
    })
# SMT part numbers for the through-hole semiconductors (same pinout roles)
SMT_VALUE = {'1N4148': '1N4148W', '1N4732 4.7V': 'BZT52C4V7 4.7V'}

parts = []


def add(ref, lib, value, units, group, fp=None, sheet='main'):
    parts.append(dict(ref=ref, lib=lib, value=value, units=units, group=group, fp=fp, sheet=sheet))


def R(ref, value, a, b, group, sheet='main'):
    add(ref, 'Device:R', value, {1: {'1': a, '2': b}}, group, FP['R'], sheet)


def C(ref, value, a, b, group, sheet='main'):
    add(ref, 'Device:C', value, {1: {'1': a, '2': b}}, group, FP['C'], sheet)


def CP(ref, value, pos, neg, group, fp='CP', sheet='main'):
    add(ref, 'Device:C_Polarized', value, {1: {'1': pos, '2': neg}}, group, FP[fp] if fp else None, sheet)


def D(ref, lib, value, k, a, group, fp='D', sheet='main'):
    if SMT and fp:
        value = SMT_VALUE.get(value, value)
    add(ref, lib, value, {1: {'1': k, '2': a}}, group, FP[fp] if fp else None, sheet)


def Q(ref, pnp, e, b, c, group, sheet='main'):
    if SMT:   # SOT-23 pads are 1 B, 2 E, 3 C; MMBT5088 stands in for the 2N5210
        lib = 'Transistor_BJT:Q_PNP_BEC' if pnp else 'Transistor_BJT:Q_NPN_BEC'
        add(ref, lib, 'MMBT5087' if pnp else 'MMBT5088', {1: {'1': b, '2': e, '3': c}}, group, FP['Q'],
            sheet)
        return
    lib = 'Transistor_BJT:Q_PNP_EBC' if pnp else 'Transistor_BJT:Q_NPN_EBC'
    add(ref, lib, '2N5087' if pnp else '2N5210', {1: {'1': e, '2': b, '3': c}}, group, FP['Q'], sheet)


# --------------------------------------------------------------------------
# Board connectors: pin positions match the original board artwork
# (docs/ac30_redblue150.jpg), pin 1 at the left seen from the component side;
# None = unused position.
# --------------------------------------------------------------------------
GRP = 'Board connectors (pin positions per original artwork)'

def conn(ref, value, nets, group=GRP, sheet='main'):
    n = len(nets)
    add(ref, f'Connector_Generic:Conn_01x{n:02d}', value,
        {1: {str(i + 1): net for i, net in enumerate(nets)}}, group,
        f'Connector_Molex:Molex_KK-396_A-41791-{n:04d}_1x{n:02d}_P3.96mm_Vertical', sheet)

if SMT:
    # Front panel wired to plain through-hole jumper pads (0.1" strips, net names on the
    # silkscreen) instead of the J1/J2 harness connectors, one strip per panel item.
    # MIC/EAR carry the audio to the RECORD A/B (S2) and PLAY A/B (S3) poles.
    def jumpers(ref, value, nets):
        n = len(nets)
        add(ref, f'Connector_Generic:Conn_01x{n:02d}', value,
            {1: {str(i + 1): net for i, net in enumerate(nets)}}, 'Front panel jumper pads',
            f'Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical')

    jumpers('J1', 'SWITCHES', [P5, G, 'CARRIER_EN_N', 'MAN_MOTOR', 'REC_SET', 'REC_RST',
                               'READ_SET', 'READ_RST', 'LOCAL_REMOTE', 'REC_RLY_DRV',
                               'READ_RLY_DRV', 'RELAY_1', 'RELAY_2'])
    jumpers('J2', 'LEDS', [P5, 'LED_REC_RDY', 'LED_READ_RDY', 'LED_REC_DATA', 'LED_READ_DATA'])
    jumpers('J13', 'MOTOR', ['MOTOR_1A', 'MOTOR_1B', 'MOTOR_2A', 'MOTOR_2B'])
    jumpers('J14', 'MIC', ['AUDIO_OUT', G])
    jumpers('J15', 'EAR', ['AUDIO_IN', G])
else:
    conn('J1', 'Front panel harness 1', ['MOTOR_1A', P5, 'LED_READ_DATA', G, 'RELAY_1', 'LED_REC_DATA',
                                         'MOTOR_1B', 'LOCAL_REMOTE', 'READ_RST', 'REC_RLY_DRV', 'MAN_MOTOR',
                                         'READ_RLY_DRV', 'RELAY_2', 'MOTOR_2A', None])
    conn('J2', 'Front panel harness 2', ['MOTOR_2B', 'READ_SET', 'REC_SET', 'REC_RST', 'LED_READ_RDY',
                                         'LED_REC_RDY', 'AUDIO_OUT', 'AUDIO_IN', 'CARRIER_EN_N', G,
                                         None, None])     # 11/12 18 VAC A/B: supply is now external
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
    5: {'14': '+13V', '1': '-13V', '7': G}}, GRP, FP['DIP14'])
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
if SMT:
    # Omron G6K-2F-Y (5 V coil, 1 A): coil 1/8; both poles (COM 3/6, NO 4/5) in parallel
    # as the normally-open motor contact; NC 2/7 unused.
    for ref, drv, a, b in (('RLY1', 'RELAY_1', 'MOTOR_1A', 'MOTOR_1B'), ('RLY2', 'RELAY_2', 'MOTOR_2A', 'MOTOR_2B')):
        add(ref, 'Relay:G6K-2', 'G6K-2F-Y 5V',
            {1: {'1': drv, '8': G, '3': a, '6': a, '4': b, '5': b, '2': None, '7': None}}, GRP, FP['RLY'])
else:
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
# Modulator / demodulator, transcribed from docs/ac30_mod_demod.pdf
# (SWTPC AC-30 Cassette Tape Modulator/Demodulator Schematic) - sheet 2.
# --------------------------------------------------------------------------
S = 'moddemod'
VP, VN = '+7.5V', '-7.5V'            # zener rails D12/D13 on the power supply

GRP = 'Modulator: CLOCK IN /2 (IC5B), /1 or /2 by DATA IN (IC5A), 2-pole filter IC4A'
add('IC5', '4xxx:4013', '4013', {
    2: {'9': 'MOD_DIV2_N', '11': 'CLOCK_IN', '10': 'CARRIER_EN_N', '8': G,
        '13': 'MOD_CLK2', '12': 'MOD_DIV2_N'},                              # IC5B
    1: {'5': 'MOD_DIV4_N', '3': 'MOD_CLK2', '4': 'MOD_RST', '6': G,
        '1': 'MOD_SQ', '2': 'MOD_DIV4_N'},                                  # IC5A
    3: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
add('IC2', '4xxx:4001', '4001', {
    1: {'1': 'DATA_IN', '2': 'MOD_EDGE', '3': 'MOD_RST'},                  # IC2A
    2: {'5': 'DEM_Q2C', '6': 'DEM_Q2C', '4': 'DEM_Q3B'},                   # IC2B
    3: {'8': 'DEM_EDGE', '9': 'DEM_EDGE', '10': 'DEM_PULSE'},              # IC2C
    4: {'12': 'DEM_PULSE', '13': 'DEM_BIT_EDGE', '11': 'DEM_CLK_N'},       # IC2D
    5: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
C('C1', '1000pF', 'MOD_CLK2', 'MOD_EDGE', GRP, S)
R('R1', '33K', 'MOD_EDGE', P5, GRP, S)
R('R2', '10K', 'MOD_SQ', 'MOD_F1', GRP, S)
R('R3', '10K', 'MOD_F1', 'MOD_F2', GRP, S)
C('C2', '2000pF', 'MOD_F2', G, GRP, S)
C('C3', '0.022uF', 'MOD_F1', 'MOD_FB', GRP, S)
add('IC4', 'Amplifier_Operational:RC4558', '4558', {
    1: {'3': 'MOD_F2', '2': 'MOD_FILT', '1': 'MOD_FILT'},                  # IC4A follower
    2: {'5': 'DEM_IN', '6': G, '7': 'DEM_CMP'},                            # IC4B comparator
    3: {'8': VP, '4': VN}}, GRP, FP['DIP8'], S)
R('R4', '330', 'MOD_FILT', 'MOD_FB', GRP, S)
R('R5', '2.2K', 'MOD_FB', G, GRP, S)
R('R6', '4.7K', 'MOD_FILT', 'MOD_ATTEN', GRP, S)
R('R7', '470', 'MOD_ATTEN', G, GRP, S)
CP('C4', '1uF 15V', 'MOD_ATTEN', 'AUDIO_OUT', GRP, sheet=S)

GRP = 'Demodulator: comparator IC4B, edge pulses IC3C/D, carrier detect, data and 16X clock out'
R('R8', '100K', 'AUDIO_IN', G, GRP, S)
C('C5', '0.01uF', 'AUDIO_IN', 'DEM_HP', GRP, S)
R('R9', '10K', 'DEM_HP', 'DEM_IN', GRP, S)
D('D1', 'Diode:1N4148', '1N4148', 'DEM_IN', G, GRP, sheet=S)
D('D2', 'Diode:1N4148', '1N4148', G, 'DEM_IN', GRP, sheet=S)
R('R10', '330K', 'DEM_IN', 'DEM_CMP', GRP, S)                          # hysteresis
R('R11', '10K', 'DEM_CMP', 'DEM_LIM', GRP, S)
D('D3', 'Device:D_Zener', '1N4732 4.7V', 'DEM_LIM', G, GRP, sheet=S)
add('IC3', '4xxx:4070', '4070', {
    3: {'8': P5, '9': 'DEM_LIM', '10': 'DEM_INV'},                         # IC3C inverter
    4: {'12': 'DEM_LIM', '13': 'DEM_DLY', '11': 'DEM_EDGE'},               # IC3D
    1: {'1': 'DEM_CD', '2': 'DEM_CD', '3': 'CARRIER_DETECT'},              # IC3A
    2: {'5': 'DEM_TIMER', '6': G, '4': 'DEM_BIT'},                         # IC3B buffer
    5: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
R('R12', '10K', 'DEM_INV', 'DEM_DLY', GRP, S)
C('C6', '1000pF', 'DEM_DLY', G, GRP, S)
R('R17', '100K', 'DEM_EDGE', 'DEM_D4', GRP, S)
D('D4', 'Diode:1N4148', '1N4148', 'DEM_D4', 'DEM_CD', GRP, sheet=S)
C('C7', '0.047uF', P5, 'DEM_CD', GRP, S)
Q('Q3', True, P5, 'DEM_Q3B_R', 'DEM_CD', GRP, S)
R('R19', '10K', 'DEM_Q3B', 'DEM_Q3B_R', GRP, S)
R('R14', '22K', 'DEM_PULSE', 'DEM_Q2B', GRP, S)                         # missing-pulse detector
Q('Q2', False, G, 'DEM_Q2B', 'DEM_Q2C', GRP, S)
R('R18', '100K', P5, 'DEM_Q2C', GRP, S)
C('C9', '0.047uF', 'DEM_Q2C', G, GRP, S)
R('R13', '22K', 'DEM_PULSE', 'DEM_Q1B', GRP, S)                         # 1200 Hz timer
Q('Q1', False, G, 'DEM_Q1B', 'DEM_TIMER', GRP, S)
R('R15', '10K', 'DEM_TIMER', 'DEM_R16', GRP, S)
add('R16', 'Device:R_Potentiometer_Trim', '20K trim', {1: {'1': 'DEM_R16', '2': P5, '3': P5}},
    GRP, FP['RT'], S)
C('C8', '0.022uF', 'DEM_TIMER', G, GRP, S)
add('IC1', '4xxx:4013', '4013', {
    1: {'5': 'DEM_BIT', '3': 'DEM_PULSE', '4': G, '6': G, '1': 'DATA_OUT', '2': None},  # IC1A
    2: {'9': G, '11': G, '10': G, '8': G, '13': None, '12': None},                     # IC1B unused
    3: {'14': P5, '7': G}}, GRP, FP['DIP14'], S)
C('C10', '2700pF', 'DEM_BIT', 'DEM_BIT_EDGE', GRP, S)
R('R20', '10K', 'DEM_BIT_EDGE', G, GRP, S)
R('R21', '10K', 'DEM_CLK_N', 'DEM_Q4B', GRP, S)
C('C11', '470pF', 'DEM_CLK_N', 'DEM_Q4B', GRP, S)
Q('Q4', False, G, 'DEM_Q4B', 'CLOCK_OUT', GRP, S)
R('R22', '10K', P5, 'CLOCK_OUT', GRP, S)

# --------------------------------------------------------------------------
# Power supply, transcribed from docs/ac30_PS.pdf (SWTPC AC-30 Audio Cassette Power
# Supply Schematic) - sheet 3.  Built as an EXTERNAL unit: no footprints, so these
# parts are in the schematic and BOM but not on the PC board.  The board takes the
# six DC outputs on J12, a 6-pin KK-396 header on the bottom edge.
# --------------------------------------------------------------------------
S = 'psu'
GRP = 'Power supply (external): 120 VAC -> T1 -> bridge D14-D17 -> +/-13 V, zeners +/-7.5 V, 7805 +5 V'
add('P1', 'Connector:Conn_Plug_2P', '120 VAC line cord', {1: {'1': 'AC_LINE', '2': 'AC_NEUTRAL'}}, GRP,
    None, S)
add('S6', 'Switch:SW_SPDT', 'POWER (SPDT, one throw used)', {1: {'2': 'AC_LINE', '1': 'AC_SW', '3': None}},
    GRP, None, S)
add('F1', 'Device:Fuse', '1A', {1: {'1': 'AC_NEUTRAL', '2': 'AC_FUSED'}}, GRP, None, S)
# Both 120 V primaries are wired in parallel on the drawing (120 VAC operation); the
# 18 VAC secondary is centre-tapped, with the tap to GND.
add('T1', 'Device:Transformer_1P_SS', '120/240V : 18VAC CT 300mA',
    {1: {'1': 'AC_SW', '2': 'AC_FUSED', '3': '18VAC_A', '4': G, '5': '18VAC_B'}}, GRP, None, S)
for ref, k, a in (('D14', '+13V', '18VAC_A'), ('D15', '+13V', '18VAC_B'),
                  ('D16', '18VAC_A', '-13V'), ('D17', '18VAC_B', '-13V')):
    D(ref, 'Diode:1N4003', '1N4003', k, a, GRP, fp=None, sheet=S)
CP('C21', '1000uF 25V', '+13V', G, GRP, fp=None, sheet=S)
CP('C22', '100uF 16V', G, '-13V', GRP, fp=None, sheet=S)
add('IC16', 'Regulator_Linear:L7805', '7805', {1: {'1': '+13V', '2': G, '3': P5}}, GRP, None, S)
add('R48', 'Device:R', '330', {1: {'1': '+13V', '2': '+7.5V'}}, GRP, None, S)
D('D12', 'Device:D_Zener', '1N4737 7.5V', '+7.5V', G, GRP, fp=None, sheet=S)
add('R49', 'Device:R', '330', {1: {'1': '-7.5V', '2': '-13V'}}, GRP, None, S)
D('D13', 'Device:D_Zener', '1N4737 7.5V', G, '-7.5V', GRP, fp=None, sheet=S)

# --------------------------------------------------------------------------
# Board side of the power supply: J12, a 6-pin KK-396 header on the bottom edge
# (same family as J1-J5) for the six DC outputs, and the +5 V bypass capacitors
# (drawn at the regulator; on the PC board on the original artwork, next to IC1,
# IC7 and IC13).
# --------------------------------------------------------------------------
GRP = 'Power input connector (from the external supply) and +5 V bypass'
conn('J12', 'Power input', [G, P5, '+13V', '-13V', '+7.5V', '-7.5V'], GRP, 'moddemod')
for c in ('C23', 'C24', 'C25'):
    C(c, '0.1uF', P5, G, GRP, 'moddemod')

# --------------------------------------------------------------------------
# BOM parts on neither schematic: listed, not placed.
# --------------------------------------------------------------------------
add('R39', 'Device:R_Potentiometer_Trim', '200K trim (DELAY)', {1: {}}, 'Not on any schematic', FP['RT'],
    'omitted')

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
          'CARRIER_EN_N': 'input', '+13V': 'passive', '-13V': 'passive',
          '+7.5V': 'passive', '-7.5V': 'passive'}
POWER = {P5: 'power:+5V', G: 'power:GND'}
