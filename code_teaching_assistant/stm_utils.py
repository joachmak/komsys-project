
def get_stm_transitions():
    t0 = {
        "source": "initial",
        "target": "unclaimed"
    }
    t1 = {
        "source": "unclaimed",
        "target": "waiting",
        "trigger": "claim_button"
    }
    t2 = {
        "source": "waiting",
        "target": "unclaimed",
        "trigger": "t",
        "effect": "timer_expired"
    }
    t3 = {
        "source": "waiting",
        "target": "claimed",
        "trigger": "sig_acc_claim"
    }
    t4 = {
        "source": "claimed",
        "target": "unclaimed",
        "trigger": "resolve_button"
    }
    t5 = {
        "source": "waiting",
        "target": "unclaimed",
        "trigger": "cancel_claim"
    }
    t6 = {
        "source": "waiting",
        "target": "unclaimed",
        "trigger": "resolve_button"
    }
    return [t0, t1, t2, t3, t4, t5, t6]


def get_stm_states():
    unclaimed = {
        "name": "unclaimed",
        "entry": "stm_log('unclaimed');",
        "sig_feedback": "stm_receive_feedback",
        "sig_help_request": "stm_receive_help_request"
    }
    waiting = {
        "name": "waiting",
        "entry": "stm_log('waiting'); start_timer('t', 5000); task_claimed",
        "sig_feedback": "stm_receive_feedback",
        "sig_help_request": "stm_receive_help_request"
    }
    claimed = {
        "name": "claimed",
        "entry": "stm_log('claimed')",
        "exit": "request_resolved",
        "sig_feedback": "stm_receive_feedback",
        "sig_help_request": "stm_receive_help_request"
    }
    return [unclaimed, waiting, claimed]


"""
TODO: Fix funksjonene:
- task_claimed
- request_resolved
- claim_button
- resolve_button
"""