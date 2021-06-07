# Shows all available commands for your TV 
#
from libLGTV_serial import LGTV

# Change this to your TV's model
model = '42LW650s'

tv = LGTV(model, 'dont_care')

# Example of adding a custom toggle command. Passing in '--toggleinput'
# will toggle between 'inputrgbpc' and 'inputdigitalcable'
tv.add_toggle('input', 'inputrgbpc', 'inputdigitalcable')

tv.available_commands()
