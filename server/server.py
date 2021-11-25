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
from threading import Thread

from bottle import Bottle, run, request, template
from bottle import response;
from bottle import HTTPresponse;
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # board stores all message on the system
    board = {0: "Welcome to Distributed Systems Course"}

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
            print e
        return success

    # This function will update an existing element in the board dictionary
    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[int(entry_sequence)] = modified_element
            success = True
        except Exception as e:
            print e
        return success

    # This function will remove an element from the board dictionary
    def delete_element_from_store(entry_sequence, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board.pop(int(entry_sequence))
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    # No need to modify this

    leader_init = False

    @app.route('/')
    def index():
        global board, node_id
        if(not leader_init):
            leader_election()
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id),
                        board_dict=sorted({"0": board, }.iteritems()), members_name_string='YOUR NAME')

    @app.post("/leader_election")
    def leader():
        leader_init = True
        print(request.forms.get('id'))
        print("Jag vill ta livet av mig")

        


    def leader_election():
      propagate_leader()

    @app.get('/board')
    def get_board():
        global board, node_id
        if(not leader_init):
            leader_election()
        print board
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))

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
            if len(board) != 0:
                element_id = int(max(board.keys()) + 1)
            else:
                element_id = 0
            add_new_element_to_store(element_id, new_entry)

            # Then we propagate the new element
            thread = Thread(target=propagate_to_vessels, args=(
                '/propagate/ADD/' + str(element_id), {'entry': new_entry}, 'POST'))
            thread.daemon = True
            thread.start()
            return True
        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        global board, node_id

        print "You receive an element"
        print "id is ", node_id
        # Get the entry from the HTTP body
        entry = request.forms.get('entry')

        delete_option = request.forms.get('delete')
        # 0 = modify, 1 = delete

        print "the delete option is ", delete_option

        # If a post request is received on board/elementid with the request data of delete = 0 we call the modify function with
        # the data received.
        if delete_option == "0":
            modify_element_in_store(element_id, entry, True)
            thread = Thread(target=propagate_to_vessels, args=(
                '/propagate/MODIFY/' + str(element_id), {'entry': entry}, 'POST'))
            thread.daemon = True
            thread.start()

        # If a post request is received on board/elementid with the request data of delete = 1 we call the delete function with
        # the data received.
        if delete_option == "1":
            delete_element_from_store(element_id, True)
            thread = Thread(target=propagate_to_vessels, args=(
                '/propagate/DELETE/' + str(element_id), {'entry': entry}, 'POST'))
            thread.daemon = True
            thread.start()


    # With this function you handle requests from other nodes like add modify or delete

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        # get entry from http body
        entry = request.forms.get('entry')
        print "the action is", action

        # Handle requests
        # for example action == "ADD":
        if action == "ADD":
            add_new_element_to_store(element_id, entry, True)

        # Modify the board entry
        if action == "MODIFY":
            modify_element_in_store(element_id, entry, True)

        # Delete the entry from the board
        if action == "DELETE":
            delete_element_from_store(element_id, True)

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    def propagate_leader():
        global node_id
        results = []
        payload = dict()
        payload["id"] = node_id
        # for vessel_id, vessel_ip in vessel_list.items():
        #    if vessel_id <= node_id:
        #        continue
        res = requests.post('http://10.1.0.2/leader_election', data=payload)
        results[vessel_id] = res

        


    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------

    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv+1):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))
        try:
            run(app, host=vessel_list[str(node_id)], port=port)
            before_first_request()
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()


except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
