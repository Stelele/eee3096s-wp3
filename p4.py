# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = None      # set if the user wins or ends the game
number_guess = 0        # current number guessed by the user
value = 1               # true answer generated by the game to be guessed by user
start_time = 0          # time when btn_submit was pressed down
score = 0               # number of guesses by the user
start_of_game = False   # checks if game has started

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy_pin = 32
LED_accuracy = None
btn_submit = 16
btn_increase = 18
buzzer_pin = 33
buzzer = None
eeprom = ES2EEPROMUtils.ES2EEPROM()

# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game
    global start_of_game
    global value
    global score
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
    elif option == "P":
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        value = generate_number()
        score = 0
        end_of_game = False
        start_of_game = True
        while not end_of_game:
            pass

        start_of_game = False
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    '''
    Prints out the top 3 scores from the eeprom
    '''
    # print the scores to the screen in the expected format
    print("There are {} scores. Here are the top 3!".format(count))

    if count == 0:
        return

    # print out the scores in the required format
    raw_data.sort(key=lambda x: x[1])
    index = 0
    stop_value = 3 if count > 3 else count
    
    while (index < stop_value):
        print("{} - {} took {} guesses".format(index+1, raw_data[index][0], raw_data[index][1]))
        index += 1
    # pass


# Setup Pins
def setup():
    # Setup board mode
    GPIO.setmode(GPIO.BOARD)

    # Setup regular GPIO
    GPIO.setup(LED_value, GPIO.OUT)
    GPIO.output(LED_value, False)

    GPIO.setup(LED_accuracy_pin, GPIO.OUT)
    GPIO.setup(buzzer_pin, GPIO.OUT)

    # Setup PWM channels
    global LED_accuracy
    global buzzer

    LED_accuracy = GPIO.PWM(LED_accuracy_pin, 100)
    LED_accuracy.start(0)
    
    buzzer = GPIO.PWM(buzzer_pin, 1)
    buzzer.ChangeDutyCycle(50)

    # Setup debouncing and callbacks
    GPIO.setup(btn_increase, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_submit, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(btn_increase, GPIO.FALLING, callback=btn_increase_pressed, bouncetime=200)

    GPIO.add_event_detect(btn_submit, GPIO.FALLING, callback=btn_guess_pressed, bouncetime=200)


# Load high scores
def fetch_scores():
    '''
    Fetches the scores from the eeprom

    :return: number of scores and 2D array containing arrays of the format ['nam': score]
    '''
    # get however many scores there are
    score_count = eeprom.read_byte(0)
    # Get the scores
    scores_raw = eeprom.read_block(1, score_count * 4)    
    # convert the codes back to ascii
    scores = []
    for i in range (0, len(scores_raw), 4):
        name_i = ''
        for j in range(i, i + 3):
            name_i += chr( scores_raw[j] )
        scores.append( [ name_i, scores_raw[i+3] ] )
    # return back the results
    return score_count, scores


# Save high scores
def save_scores(new_score):
    # fetch scores
    count, scores = fetch_scores()
    # include new score
    scores.append(new_score)
    # sort
    scores.sort(key=lambda x: x[1])
    # update total amount of scores
    count += 1
    # write new scores
    data_to_write = []
    for score in scores:
        for letter in score[0]:
            data_to_write.append(ord(letter))
        data_to_write.append(score[1])
    eeprom.write_block(0, [count])
    eeprom.write_block(1, data_to_write)
    # pass


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):
    # Increase the value shown on the LEDs
    # You can choose to have a global variable store the user's current guess, 
    # or just pull the value off the LEDs when a user makes a guess

    global number_guess
    global start_of_game

    if not start_of_game:
        return
    
    number_guess =  (number_guess + 1) % 8

    value = 1

    for led in LED_value:
        GPIO.output(led, number_guess & value)
        value = value << 1
    


# Guess button
def btn_guess_pressed(channel):
    if not start_of_game:
        return

    # Get button press time
    tick()
    while GPIO.input(btn_submit) == False:
        time.sleep(0.01)

    time_elapsed = tock()

    # Compare the actual value with the user value displayed on the LEDs
    global value
    global number_guess
    global end_of_game
    global buzzer
    global LED_accuracy
    global score

    offset = abs(value - number_guess)

    # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
    long_press_threshold = 1
    if time_elapsed >= long_press_threshold:
        number_guess = 0
        score = 0

        GPIO.output(LED_value, False)
        buzzer.stop()
        LED_accuracy.stop()

        welcome()
        end_of_game = True

    else:
        # increment number of guesses
        score += 1

        # Change the PWM LED
        accuracy_leds()

        # if it's close enough, adjust the buzzer
        trigger_buzzer()

        # if it's an exact guess:
        if(offset == 0):
            # - Disable LEDs and Buzzer
            GPIO.output(LED_value, False)
            buzzer.stop()
            LED_accuracy.stop()

            number_guess = 0

            # - tell the user and prompt them for a name
            name = ""
            print("Congradulations!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

            while True:
                name = input("Please enter name, Must not be more than 3 characters :)\n")

                if len(name) <= 3:
                    break

            # save score
            # - add the new score
            # - sort the scores
            # - Store the scores back to the EEPROM, being sure to update the score count
            save_scores([name , score ])

            # - Return to main menue
            welcome()
            end_of_game = True
            
# LED Brightness
def accuracy_leds():
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    # - For example if the answer is 6 and a user guesses 4, the brightness should be at 4/6*100 = 66%
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%
    global value
    global number_guess
    global accuracy_leds

    offset = abs(value - number_guess)
    dc = ((8-offset)/8)*100

    LED_accuracy.ChangeDutyCycle(dc)


# Sound Buzzer
def trigger_buzzer():
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    
    global value
    global number_guess
    global buzzer

    offset = abs(value - number_guess)

    if offset == 3:
        buzzer.ChangeFrequency(1)
    elif offset == 2:
        buzzer.ChangeFrequency(2)
    elif offset == 1:
        buzzer.ChangeFrequency(4)
    

    if offset < 4:
        buzzer.start(50)
    else:
        buzzer.stop()

# get set start time
def tick():
    global start_time

    start_time = time.time()

# get time elapsed
def tock():
    global start_time

    return time.time() - start_time

if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
            pass
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()
