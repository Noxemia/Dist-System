# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: John Doe
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
import random
from threading import Thread

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # board stores all message on the system
    board = {0: "Welcome to Distributed Systems Course"}
    seq_board = {0:'0'}

    sequenser = 1

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # You will probably need to modify them
    # ------------------------------------------------------------------------------------------------------

    # This functions will add an new element

    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            if entry_sequence not in board:
                board[int(entry_sequence)] = element
                success = True
        except Exception as e:
            print(e)
        return success

    # This function will update an existing element in the board dictionary
    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[int(entry_sequence)] = modified_element
            success = True
        except Exception as e:
            print(e)
        return success

    # This function will remove an element from the board dictionary
    def delete_element_from_store(entry_sequence, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board.pop(int(entry_sequence))
            success = True
        except Exception as e:
            print(e)
        return success

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    # No need to modify this
    @app.route('/')
    def index():
        global board, node_id
        thread=Thread(target=get_consistency)
        thread.daemon=True
        thread.start()


        return template('server/index.tpl', board_title='Vessel {}'.format(node_id),
                        board_dict=sorted({"0": board, }.iteritems()), members_name_string='YOUR NAME')

    @app.get('/board')
    def get_board():
        global board, node_id
        print(board)
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))

    @app.get('/get_board')
    def get_board():
        global board
        return json.dumps({"board": board, 'seq_board': seq_board})

    seq = 0

    @app.get('/sequence')
    def get_sequence():
        global seq, node_id
        print("Hello World!", node_id)
        if node_id == sequenser:
            print("Hello World!")
            seq += 1
            retval = json.dumps({"seq": str(seq)})
            print(retval)
            return {"seq": seq}

    # ------------------------------------------------------------------------------------------------------

    # You NEED to change the follow functions
    @app.post('/board')
    def client_add_received():
        '''Adds a new element to the board
        Called directly when a user is doing a POST request on /board'''
        global board, node_id
        try:
            new_entry = request.forms.get('entry')
            # When generating an ID for a new element we take the largest ID(key) in the dictionary and add one
            # if the dictionary is empty we start at 0
            res = requests.get('http://10.1.0.1/sequence')
            seq = 0
            if res.status_code == 200:
                seq = res.json().get('seq')
                print("Sequence: ", seq)
            else:
                print("Sequencer failed!!!")

            element_id = str(random.randint(0, 1000))
            while element_id in board:
                element_id = str(random.randint(0, 1000))
            add_new_element_to_store(element_id, new_entry)

            # Then we propagate the new element
            thread=Thread(target=propagate_to_vessels, args=(
                '/propagate/ADD/' + str(element_id), {'entry': new_entry, 'seq': seq}, 'POST'))
            thread.daemon=True
            thread.start()
            return True
        except Exception as e:
            print(e)
        return False

    @ app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, node_id

        print("You receive an element")
        print("id is "), node_id
        # Get the entry from the HTTP body
        entry=request.forms.get('entry')

        delete_option=request.forms.get('delete')
        # 0 = modify, 1 = delete

        print("the delete option is "), delete_option

        # If a post request is received on board/elementid with the request data of delete = 0 we call the modify function with
        # the data received.
        if delete_option == "0":
            modify_element_in_store(element_id, entry, True)
            thread=Thread(target=propagate_to_vessels, args=(
                '/propagate/MODIFY/' + str(element_id), {'entry': entry}, 'POST'))
            thread.daemon=True
            thread.start()

        # If a post request is received on board/elementid with the request data of delete = 1 we call the delete function with
        # the data received.
        if delete_option == "1":
            delete_element_from_store(element_id, True)
            thread=Thread(target=propagate_to_vessels, args=(
                '/propagate/DELETE/' + str(element_id), {'entry': entry}, 'POST'))
            thread.daemon=True
            thread.start()


    # With this function you handle requests from other nodes like add modify or delete

    @ app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        # get entry from http body
        entry=request.forms.get('entry')
        seq=request.forms.get('seq')
        print("the action is"), action

        # Handle requests
        # for example action == "ADD":
        if action == "ADD":
            seq_board[element_id] = seq
            add_new_element_to_store(element_id, entry, True)

        # Modify the board entry
        if action == "MODIFY":
            seq_board[element_id] = seq
            modify_element_in_store(element_id, entry, True)

        # Delete the entry from the board
        if action == "DELETE":
            seq_board[element_id] = -1
            delete_element_from_store(element_id, True)

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success=False
        try:
            if 'POST' in req:
                res=requests.post(
                    'http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                res=requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print('Non implemented feature!')
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success=True
        except Exception as e:
            print(e)
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success=contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print("\n\nCould not contact vessel {}\n\n".format(vessel_id))

    def get_consistency():
        global board,  vessel_list, node_id, seq_board
        print("I got called")

        boards=[]
        seq_boards = []

        boards.append(board)
        seq_boards.append(seq_board)
        test = {"xd": "lmao"}
        testj = json.dumps(test)
        testb = json.loads(testj)
        print(testb, "\n")
        print(type(testj), " ---  ", type(testb))

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                res=requests.get('http://{}/get_board'.format(vessel_ip))
                if res.status_code == 200:
                    boards.append(res.json().get('board'))
                    seq_boards.append(res.json().get('seq_board'))
        #print(boards)
        #print(seq_boards)
        # board(msgid: msg)
        # seq_board(msgid: seq)
        # dict = {msgid: (seq, msg)}
        data = {}
        for i in range((len(seq_boards))):
            for k in seq_boards[i].keys():
                data[str(k)] = (-2, "")



        for i in range(len(boards)):
            iseq_board = seq_boards[i]
            iboard = boards[i]
            for id in iseq_board.keys():
                print(id)
                try:
                    msg = iboard.get(id)
                    seq_bm = int(iseq_board.get(id))
                    print("Msg and seq_bm", msg, "-----",seq_bm)
                    if  seq_bm > int(data.get(id)[0]) and int(data.get(id)[0]) != -1:
                        data[id] = (seq_bm, msg)
                    if seq_bm == -1:
                        data[id] = (seq_bm, None)
                except Exception as e:
                    print(e)
        newboard = {}
        newseq_board = {}

        for id in data.keys():
            newseq = data.get(id)[0]   
            newseq_board[id] = newseq
            if newseq != -1:
                newboard[id] = data.get(id)[1]
            
        board = newboard
        seq_board = newseq_board
                


    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------

    def main():
        global vessel_list, node_id, app

        port=80
        parser=argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args=parser.parse_args()
        node_id=args.nid
        vessel_list=dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv+1):
            vessel_list[str(i)]='10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print(e)
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()


except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
