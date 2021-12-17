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
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # board stores all message on the system
    board = {0: "Welcome to Distributed Systems Course"}

    votes = []

    # Simple methods that the byzantine node calls to decide what to vote.
    # Compute byzantine votes for round 1, by trying to create
    # a split decision.
    # input:
    # number of loyal nodes,
    # number of total nodes,
    # Decision on a tie: True or False
    # output:
    # A list with votes to send to the loyal nodes
    # in the form [True,False,True,.....]

    def compute_byzantine_vote_round1(no_loyal, no_total, on_tie):
        result_vote = []
        for i in range(0, no_loyal):
            if i % 2 == 0:
                result_vote.append(not on_tie)
            else:
                result_vote.append(on_tie)
        return result_vote
    # Compute byzantine votes for round 2, trying to swing the decision
    # on different directions for different nodes.
    # input:
    # number of loyal nodes,
    # number of total nodes,
    # Decision on a tie: True or False
    # output:
    # A list where every element is a the vector that the
    # byzantine node will send to every one of the loyal ones
    # in the form [[True,...],[False,...],...]

    def compute_byzantine_vote_round2(no_loyal, no_total, on_tie):

        result_vectors = []
        for i in range(0, no_loyal):
            if i % 2 == 0:
                result_vectors.append([on_tie]*no_total)
            else:
                result_vectors.append([not on_tie]*no_total)
        return result_vectors
    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # You will probably need to modify them
    # ------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    # No need to modify this

    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id),
                        board_dict=sorted({"0": board, }.iteritems()), members_name_string='YOUR NAME')

    @app.get('/board')
    def get_board():
        global board, node_id
        print(board)
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))

    # ------------------------------------------------------------------------------------------------------

    @app.post('/vote/attack')
    def vote_attack():
        global votes
        votes.append(True)
        print(votes)
        thread = Thread(target=propagate_to_vessels,
                        args=('/vote/attack', None, 'POST'))
        thread.daemon = True
        thread.start()

    @app.post('/vote/retreat')
    def vote_attack():
        global votes
        votes.append(False)
        print(votes)

    @app.get('/vote/result')
    def vote_results():
        global votes
        return json.dumps(votes)

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
                print('Non implemented feature!')
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print(e)
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print("\n\nCould not contact vessel {}\n\n".format(vessel_id))

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
        except Exception as e:
            print(e)
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()


except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
