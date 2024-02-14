# import the relevant packages:
from psychopy import visual, event, core
import scannertrigger as s
import pyxid2

# create a window with size = screen resolution of stimulus computer:
window = visual.Window(size = [1024, 768], color = 'white', fullscr = True)

# create a stimulus object:
text = visual.TextStim(window, color = 'black')

# initiate a clock:
clock = core.Clock()

# prepare to align timing of behavioural and fMRI data:
st = s.ScannerTrigger.create(window, clock, portType = 'cedrus', portConfig = {'devicenr': 0, 'sync': 4}, timeout = 999999, esc_key = 'escape')
st.open()
dev = st.port

# let the participant in the scanner know that scanning will begin shortly:
text.text = 'Scanning will begin shortly.'
text.draw()
window.flip()

# when ready, press space to let the script wait for the scanner to start scanning, afterwards (!) start scanning:
startBlock = event.waitKeys(keyList = ['space'])

# let the script continue at the start of functional scan 6 (with TR = 2 seconds, after 10 seconds of scanning):
try:
    text.draw()
    window.flip()
    print('waiting for Scanner')
    triggered = st.waitForTrigger(skip = 5)
    print('scanner OK')
except Exception as e:
    print('scanner error: {0}'.format(e))
    core.quit()

# reset the clock as soon as the script continues (!) to be able to align timing of bahiouvoral and fMRI data during the analyses:
clock.reset()

# prepare to present the stimulus:
text.text = 'Press the button under your left index finger.'
text.draw()

# but make sure there are no more old responses left in the response box first:
dev.poll_for_response()
while len(dev.response_queue):
    dev.clear_response_queue()
    dev.poll_for_response()

# present the stimulus:
window.flip()

# wait for the participant to give the correct response:
val = 0
while val == 0:
    while not dev.has_response():
        dev.poll_for_response()
    resp = dev.get_next_response()
    
    if resp['key'] == 1: # left middle finger = 0, left index finger = 1, right index finger = 2, right middle finger = 3
        respTime = clock.getTime() # in the fMRI data, the time the participant gave the correct response = respTime + 5 times the TR (because we reset the clock at the beginning of scan 6)
        val = 1

# let the participant in the scanner know that scanning will stop shortly:
text.text = 'Scanning will stop shortly.'
text.draw()
window.flip()

# press space to close the script:
endBlock = event.waitKeys(keyList = ['space'])

st.close()    
core.quit()
