import cv2
from modules.HandDetectorModule_1 import HandDetector as htm
import mediapipe as mp
import time
import cvzone
import random

cap = cv2.VideoCapture(0)                   #Camera capture
hand_detector = htm()                       #Instancing the HandDetector class

def find_score(label, handList):            #Function to evaluate score from hand gesture, label specifies hand position
    fingers = []
    tipIds = [8, 12, 16, 20]

    def isThumbsUp(label, handList):
        #Function to check whether only the thumb is up and rest others down, to result in a six
        thumb_tip_y = handList[4][2]
        thumb_ip_y = handList[3][2]

        index_tip_x = handList[8][1]
        index_mcp_x = handList[7][1]

        middle_tip_x = handList[12][1]
        middle_mcp_x = handList[11][1]

        ring_tip_x = handList[16][1]
        ring_mcp_x = handList[15][1]

        pinky_tip_x = handList[20][1]
        pinky_mcp_x = handList[19][1]

        thumb_up = thumb_tip_y < thumb_ip_y  

        if label == "Right":
            fingers_down = (
                index_tip_x > index_mcp_x and
                middle_tip_x > middle_mcp_x and
                ring_tip_x > ring_mcp_x and
                pinky_tip_x > pinky_mcp_x
            )

        else:
            fingers_down = (
                index_tip_x < index_mcp_x and
                middle_tip_x < middle_mcp_x and
                ring_tip_x < ring_mcp_x and
                pinky_tip_x < pinky_mcp_x
            )

        return thumb_up and fingers_down

    if isThumbsUp(label, handList):
        return [6, 0, 0, 0, 0], 6

    # For normal 5-finger scoring
    fingers.append(1 if handList[4][2] < handList[3][2] else 0)         #Thumb up or down

    for id in tipIds:                                                   #Rest four fingers logic
        if label == "Right":
            fingers.append(1 if handList[id][1] < handList[id - 1][1] else 0)       
        elif label == "Left":
            fingers.append(1 if handList[id][1] > handList[id - 1][1] else 0)

    score = sum(fingers)
    return fingers, score


'''
 <--- Flag and state variables used in the program --->

'''

scores = {'Left' : 0, 'Right' : 0}                  #Dictionary to store scores of both hands
curr_batter = None                                  #Current batter
waitingForValidInput = True                         #State variable to take input, only when both wrists show a non-zero value/run (You are not Babar Azam, why play dots?)
first_innings_score = 0                             #Sets target for second innings
gameOver = False                                    #Variable to check whether both innings are over
last_scored_time = 0                                #Variable to store move time for cool-down purpose
cooldown_duration = 2                               #Cool-down variable, can be changed to improve UX
innings = 1                                         #Innings variable, 1 for first innings, 2 for second
waiting_for_second_innings = False                  #When first innings is over, this remains false until ENTER is pressed, to start second innings smoothly
game_start = 0                                      #Flag for game state (0 or 1)
mode_of_toss_chosen = False                         #Flag to check user's choice state for toss  
toss_made = False                                   #Toss state 
tossing = False                                     #Ongoing toss state
toss_winner = None                                  #To store toss winner, left or right player
toss_choice_made = False                            #Flag to store whether the toss winner has chosen bat or field
random_toss = False                                 #For random PC generated toss
manual_toss = False                                 #For manual finger-counting toss
waiting_for_bat_bowl_choice = False                 #To manage bat or field choice flow
toss_detected = False                               #For manual toss, flag for toss detection
toss_detected_time = 0                              #For cool-down purposes in manual toss
left_choice = ""                                    #To store Heads or Tails for the left player and the right player automatically gets assigned the opposite
post_input_buffer = 1.5                             #Buffer before countdown to move starts
input_processed_time = 0                            #To evaluate time for the buffer above
score_updated = False                               #Flag to check whether the score has been updated or not

# Anti-Cheat Addition
left_move_time = 0
right_move_time = 0
move_time_threshold = 0.5  # seconds



''' <--- Game loop, all of it occurs here --->'''

while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    if not success or img is None:
        print("Failure")
        continue

    img = hand_detector.findHands(img, True, False)
    handsList = hand_detector.findPosition(img)
    currentTime = time.time()

    if game_start == 0:                             #Game not started yet
        cv2.putText(img, "Press Space to start the game", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

 
    if game_start == 1 and not mode_of_toss_chosen and not toss_made:               #Game started, choose toss mode
        cv2.putText(img, "Press 'Z' for Random PC Toss", (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(img, "Press 'X' for Manual Hand Toss", (80, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)



    ''' <--- Random tossing ---> '''
 
    if random_toss and tossing and mode_of_toss_chosen and not toss_made and toss_choice_made:           #Random toss block
        elapsed_time = time.time() - toss_message_start_time
        if elapsed_time < 5:
            cv2.putText(img, "Tossing...", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

        else:
            t = random.choice(['Heads', 'Tails'])
            if t == left_choice:
                toss_winner = 'Left'
            else:
                toss_winner = 'Right'
            cv2.putText(img, f"{toss_winner} wins the toss!", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)
            # You can then decide batting/fielding, or wait for user to press a key to proceed
            tossing = False
            cv2.putText(img, "Press 'B' to bat, 'F' to field", (80, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
            waiting_for_bat_bowl_choice = True
            #last_scored_time = time.time()
            #toss_made = True




        ''' <--- Manual tossing --->'''

    elif (manual_toss or random_toss) and not toss_choice_made and not toss_made:                    #Manual toss block, choose Heads or Tails for the left player and the right player automatically gets assigned the opposite
        cv2.putText(img, "Left player: Press 'H' for Heads or 'T' for Tails", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    elif manual_toss and toss_choice_made and not toss_detected and not toss_made:  #Manual toss block, detect the players' fingers to toss
        elapsed_time = time.time() - toss_message_start_time
        if elapsed_time >= 3 :
            cv2.putText(img, "Manual Toss: Show numbers on both hands", (80, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

            if len(handsList) == 2:                                                 #Similar as scoring runs
                dict1 = handsList[0]
                dict2 = handsList[1]

                if dict1['lmList'][0][1] < dict2['lmList'][0][1]:
                    leftHand = dict1['lmList']
                    rightHand = dict2['lmList']
                else:
                    leftHand = dict2['lmList']
                    rightHand = dict1['lmList']

                left_toss = find_score("Left", leftHand)[1]
                right_toss = find_score("Right", rightHand)[1]

                if left_toss != 0 and right_toss != 0:                          
                  total = left_toss + right_toss                                      #General hand toss logic : Odd -> Heads, Even -> Tails
                  toss_result = 'Heads' if total % 2 == 1 else 'Tails'

                  if toss_result == left_choice:
                      toss_winner = 'Left'
                  else:
                      toss_winner = 'Right'

                  toss_detected = True
                  waiting_for_bat_bowl_choice = True
                  toss_detection_time = time.time()

    elif waiting_for_bat_bowl_choice and not toss_made:                                 #Toss done, winner gets to choose batting or bowling
        cv2.putText(img, f"{toss_winner} won the toss!", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        cv2.putText(img, "Press 'B' to Bat or 'F' to Field", (120, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

    elif toss_detected and time.time() - toss_detection_time < 7 and not toss_made:                 #Cooldown (UX)                          
        cv2.putText(img, f"Toss Result: {toss_result}", (180, 190), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)             
        cv2.putText(img, f"{toss_winner} wins the toss!", (150, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)           
                                                                                                                               
    elif toss_detected and time.time() - toss_detection_time >= 7:                                  #Cooldown (UX)
        #waiting_for_bat_bowl_choice = True                                                                                    
        #manual_toss = False                                                                                                
        toss_made = True       





        ''' <--- Actual game, the PITCH ---> '''                                                                                                 
    

    if not gameOver and currentTime - last_scored_time > cooldown_duration and not waiting_for_second_innings and game_start == 1 and toss_made:

        if len(handsList) == 2:
            dict1 = handsList[0]
            dict2 = handsList[1]

            # Assigning hands according to position relative to camera and screen
            if dict1['lmList'][0][1] < dict2['lmList'][0][1]:
                leftHand = dict1['lmList']
                rightHand = dict2['lmList']

            else:
                leftHand = dict2['lmList']
                rightHand = dict1['lmList']

            #Get scores according to the hand position, left and right (note that the image being captured in flipped for a direct experience)
            left_score = find_score("Left", leftHand)[1]
            right_score = find_score("Right", rightHand)[1]

            if not score_updated and left_score != 0 and right_score != 0 :
                input_processed_time = time.time()
                waitingForValidInput = False
                #played_score = left_score if curr_batter == 'Left' else right_score
                #opposing_score = right_score if curr_batter == 'Right' else left_score
                if left_score == right_score:

                    #First innings OUT
                    if innings == 1:
                        innings = 2
                        first_innings_score = scores[curr_batter]
                        curr_batter = 'Right' if curr_batter == 'Left' else 'Left'
                        scores[curr_batter] = 0
                        last_scored_time = currentTime
                        waiting_for_second_innings = True

                    else:
                        #Second innings OUT
                        gameOver = True

                else:
                    scores[curr_batter] += left_score if curr_batter == 'Left' else right_score
                    if innings == 2 and scores[curr_batter] > first_innings_score:
                        gameOver = True
                last_scored_time = input_processed_time + post_input_buffer
                waitingForValidInput = True
                score_updated = True

            else:
                waitingForValidInput = True

        else:
            waitingForValidInput = True

    if gameOver:
        winner_text = "Match Drawn"
        if scores[curr_batter] > first_innings_score:
            winner_text = f"{curr_batter} Wins!"
        elif scores[curr_batter] < first_innings_score:
            cv2.putText(img, "YOU'RE OUT!", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            winner_text = f"{'Right' if curr_batter == 'Left' else 'Left'} Wins!"

        cv2.putText(img, winner_text, (180, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, "Press 'R' to Restart", (180, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    elif waiting_for_second_innings and game_start == 1:
        # Prompt to start second innings manually
        cv2.putText(img, "YOU'RE OUT!", (200, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.putText(img, "Press ENTER to Start Second Innings", (100, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)


    # Prompt users to show hand gestures after cool-down
    elif waitingForValidInput and not waiting_for_second_innings and not gameOver and game_start == 1 and toss_made:
        time_left = cooldown_duration - (currentTime - last_scored_time)
        if time_left >= 0 and time_left <= cooldown_duration:
            cv2.putText(img, f"Get Ready... {int(time_left) + 1}", (150, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
        elif time_left < 0:
            cv2.putText(img, "Show your hand gestures now!", (100, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 102, 255), 2)
            score_updated = False

    if game_start == 1 and not waiting_for_second_innings and toss_made:  
        cv2.putText(img, f"Score : {scores[curr_batter]}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(img, f"{curr_batter}'s Innings - {innings}st", (350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    
    if innings == 2:
        cv2.putText(img, f"Target : {first_innings_score + 1}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)


    cv2.imshow('Image', img)
    
    
    key = cv2.waitKey(1)




    ''' <--- Input handling ---> '''

    if key == ord('r'):                                         #Restart, all state variables returned to default for replay 
        gameOver = False
        last_scored_time = time.time()
        scores = {'Left': 0, 'Right': 0}
        waitingForValidInput = True
        curr_batter = None
        innings = 1
        waiting_for_second_innings = False
        first_innings_score = 0
        game_start = 0
        mode_of_toss_chosen = False                                     
        toss_made = False
        tossing = False
        toss_winner = None 
        toss_choice_made = False
        random_toss = False
        manual_toss = False
        waiting_for_bat_bowl_choice = False
        toss_detected = False
        toss_detected_time = 0
        left_choice = ""

    elif key == 13: # ENTER KEY                               #To start second innings after first innings has ended
        if waiting_for_second_innings:
            waiting_for_second_innings = False
            last_scored_time = time.time()

    elif key == 32:                                           #Very beginning, to start the game
        game_start = 1

    elif key == ord('z') and game_start == 1 and not random_toss:           #Choosing random toss mode
        random_toss = True
        tossing = False
        toss_detected = False
        mode_of_toss_chosen = True
        toss_choice_made = False
        toss_message_start_time = time.time()

    
    elif key == ord('x') and game_start == 1 and not manual_toss:           #Choosing manual toss mode
        manual_toss = True
        toss_detected = False
        mode_of_toss_chosen = True
        toss_choice_made = False
        left_choice = ""


    elif waiting_for_bat_bowl_choice:                                       #Batting or bowling choice
        if key == ord('b'):
            curr_batter = toss_winner
            waiting_for_bat_bowl_choice = False
            game_start = 1
            last_scored_time = time.time()
            toss_made = True

        elif key == ord('f'):
            curr_batter = 'Right' if toss_winner == 'Left' else 'Left'
            waiting_for_bat_bowl_choice = False
            game_start = 1
            last_scored_time = time.time()
            toss_made = True


    
    elif (manual_toss or random_toss) and not toss_choice_made and key == ord('h'):         #Left player chooses head
        left_choice = 'Heads'
        right_choice = 'Tails'
        toss_choice_made = True
        tossing = True
        toss_message_start_time = time.time()

    elif (manual_toss or random_toss) and not toss_choice_made and key == ord('t'):         #Left player chooses tail
        left_choice = 'Tails'
        right_choice = 'Heads'
        toss_choice_made = True
        tossing = True
        toss_message_start_time = time.time()

    elif key == ord('q'):                                                  #Quit the game anytime
        break





cap.release()
cv2.destroyAllWindows()
