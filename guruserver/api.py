import json
from flask import request
from flask_restful import Api
from flask_restful import Resource
from flask_restful import abort
from .app import app
from .schema import Policy as PolicyDB
from .policy import train_policy
from .policy import predict_policy

api = Api(app)


class Policy(Resource):

    def get(self, **args):
        """Get policy."""
        if 'policy_id' not in args:
            return abort(404, message='Must provide a policy id')
        else:
            policy = PolicyDB.objects.get_or_404(id=args['policy_id'])
            return {'policy': policy.pomdp_policy,
                    'config': policy.config,
                    'histories': policy.histories}

    def post(self, **args):
        """Train policy or make prediction.

        Json arguments for /policies endpoint:
            config (dict): Configuration.
            histories (Optional[list]): Worker histories.

        config arguments:
            model (dict): Model specification.
            policy (dict): Policy specification. If policy['epsilon'] not
                given, model parameters are fixed and not estimated (no RL).
            budget_spent (Optional[float]): Budget spent.
            budget_explore (Optional[float]): Budget explore.
            resolve_random_restarts (Optional[int]): Number of random restarts
                to use during model estimation. Defaults to 5.

        Json arguments for /policies/<policy_id> endpoint:
            history (Optional[list]): Worker history.
            mode (str): Can be 'rl' or 'exploit'.
            budget_spent (Optional[float]): Budget spent.
            budget_explore (Optional[float]): Budget explore.
            previous_workers (Optional[int]): Number of previous workers.

        TODO(jbragg): Consider moving mode, budget_spent, and budget_explore to /policies endpoint only.

        """
        json_args = request.get_json()
        if 'policy_id' not in args:
            # Train new policy.
            if 'config' not in json_args:
                abort(400, message='Please provide config')
            histories = json_args.get('histories', None)
            estimate = json_args.get('estimate', True)
            policy = PolicyDB(config=json_args['config'],
                              histories=histories).save()
            policy_id = str(policy.id)
            train_policy.delay(policy_id=policy_id)
            return {'id': policy_id}
        else:
            # Do something with existing policy.
            mode = json_args.get('mode', None)
            budget_spent = json_args.get('budget_spent', None)
            budget_explore = json_args.get('budget_explore', None)
            previous_workers = json_args.get('previous_workers', None)
            if mode in ['rl', 'exploit']:
                history = json_args.get('history', [])
                action, explore_p = predict_policy(
                    policy_id=args['policy_id'], history=history,
                    exploit=(mode == 'exploit'),
                    budget_spent=budget_spent,
                    budget_explore=budget_explore,
                    previous_workers=previous_workers)
                return {'action': action,
                        'explore': explore_p}
            else:
                return abort(400, message='Please provide a valid mode')


api.add_resource(Policy, '/policies', '/policies/<policy_id>')
