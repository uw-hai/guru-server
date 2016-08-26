import os
import cPickle as pickle
from .schema import Policy as PolicyDB
from .guru.research_utils.util import ensure_dir
from .guru.policy import Policy
from .guru.param import Params
from .guru.history import History
from .guru.work_learn_problem import Action
from .app import TMP_DIR
from .app import celery

MODELS_DIR = os.path.join(TMP_DIR, 'models')
POLICIES_DIR = os.path.join(TMP_DIR, 'policies')
N_RANDOM_RESTARTS = 10


def load_history(histories, policy):
    """Return Guru history.

    Args:
        histories (list): Worker histories.
        policy (.guru.policy.Policy): Policy object.

    Returns:
        .guru.history.History: Guru history.

    """
    history_obj = History()
    for worker_history in histories:
        history_obj.new_worker()
        for history_entry in worker_history:
            action_index = policy.model.actions.index(
                Action(**history_entry['action']))
            observation_index = policy.model.observations.index(
                history_entry['observation'])
            history_obj.record(action=action_index,
                               observation=observation_index)
    return history_obj


@celery.task
def train_policy(policy_id):
    """Train a policy.

    Assumes all actions in history have an observation.
    Will always solve a policy so that exploitation is possible.

    Args:
        policy_id (str): Policy ID.

    """
    # TODO(jbragg): BIC model selection.
    policy_doc = PolicyDB.objects(id=policy_id).first()

    params = Params.from_cmd(policy_doc.config['model'])
    policy_dict = policy_doc.config['policy']

    policy = Policy(policy_type=policy_dict['type'],
                    n_worker_classes=params.n_classes,
                    params_gt=params.get_param_dict(sample=False),
                    **policy_dict)

    ensure_dir(MODELS_DIR)
    ensure_dir(POLICIES_DIR)
    pomdp_fpath = os.path.join(MODELS_DIR, '{}.pomdp'.format(policy_id))
    policy_fpath = os.path.join(POLICIES_DIR, '{}.policy'.format(policy_id))

    # TODO(jbragg): Don't use these defaults.
    # TODO(jbragg): Look into loading history as in guru.simulator -> guru.pomdp.main()
    # Also note utility.models.teach_history.TeachHistory.add_to_phistory().
    if policy_doc.histories is not None:
        history = load_history(histories=policy_doc.histories, policy=policy)
    else:
        history = History()
    budget_spent = policy_doc.config.get('budget_spent', None)
    budget_explore = policy_doc.config.get('budget_explore', None)
    reserved = False
    resolve_min_worker_interval = None  # Resolve as often as possible.
    resolve_max_n = None  # No limit on resolving.
    resolve_random_restarts = policy_doc.config.get(
        'resolve_random_restarts', N_RANDOM_RESTARTS)
    policy.prep_worker(
        model_filepath=pomdp_fpath,
        policy_filepath=policy_fpath,
        history=history,
        budget_spent=budget_spent,
        budget_explore=budget_explore,
        reserved=reserved,
        resolve_min_worker_interval=resolve_min_worker_interval,
        resolve_random_restarts=resolve_random_restarts,
        resolve_max_n=resolve_max_n)
    # policy.model.estimate(history=history,
    #                      last_params=False,  # TODO(jbragg: fix)
    #                      random_restarts=resolve_random_restarts)
    # self.external_policy = self.run_solver(
    #        model_filepath=pomdp_fpath,
    #        policy_filepath=policy_fpath)
    if policy.external_policy is not None:
        with open(policy_fpath, 'r') as f:
            policy_doc.pomdp_policy = f.read()
    # TODO(jbragg): save model
    policy_doc.policy = pickle.dumps(policy)
    policy_doc.status = 'trained'
    policy_doc.save()


def predict_policy(policy_id, history=None, exploit=False,
                   budget_spent=None, budget_explore=None,
                   previous_workers=None):
    """Use policy to recommend next action.

    Args:
        policy_id (str): Policy ID.
        history (list): Worker history.
        exploit (bool): Force exploitation.
        budget_spent (Optional[float]): Budget spent thus far.
            Will exploit if not provided.
        budget_explore (Optional[float]): Budget allowed for exploring.
            Will exploit if not provided.
        previous_workers (Optional[int]): Number of previous workers.

    Returns:
        dict: Dictionary describing action.
        bool: True iff exploring action.

    """
    policy_doc = PolicyDB.objects(id=policy_id).first()
    policy = pickle.loads(policy_doc.policy)

    if history is None:
        history = []
    policy_history = load_history(histories=[history], policy=policy)
    # TODO(jbragg): Don't need to do this for fixed policies? (Optimization)
    belief = policy.model.get_start_belief()
    for a, o, _ in policy_history.history[-1]:
        belief = policy.model.update_belief(belief, a, o)

    if exploit or budget_spent is None or budget_explore is None:
        action_index = policy.get_best_action(
            history=policy_history, belief=belief)
        explore = False
    else:
        policy.set_use_explore_policy(
            worker_n=previous_workers,
            budget_spent=budget_spent,
            budget_explore=budget_explore,
            t=policy_history.n_t(0))
        action_index, explore = policy.get_next_action(
            history=policy_history, belief=belief,
            budget_spent=budget_spent, budget_explore=budget_explore)
    return policy.model.actions[action_index].__dict__, explore
