
def get_stm_transitions():
    t0 = {
        "source": "initial",
        "target": "unsent"
    }
    t1 = {
        "source": "unsent",
        "target": "sent",
        "trigger": "click"
    }
    t2 = {
        "source": "sent",
        "target": "unsent",
        "trigger": "click"
    }
    t3 = {
        "source": "sent",
        "target": "sent",
        "trigger": "sig_queue",
        "effect": "update_queue_position"
    }
    t4 = {
        "source": "sent",
        "target": "confirmed",
        "trigger": "sig_claim",
        "effect": "accept_claim"
    }
    t5 = {
        "source": "confirmed",
        "target": "sent",
        "trigger": "sig_unclaim",
        "effect": "unclaim"
    }
    t6 = {
        "source": "confirmed",
        "target": "confirmed",
        "trigger": "sig_claim",
        "effect": "reject_claim"
    }
    t7 = {
        "source": "confirmed",
        "target": "unsent",
        "trigger": "sig_resolve",
        "effect": "resolve_request"
    }
    return [t0, t1, t2, t3, t4, t5, t6, t7]


def get_stm_states():
    unsent = {
        "name": "unsent",
        "entry": "stm_log('unsent')"
    }
    sent = {
        "name": "sent",
        "entry": "stm_log('sent')"
    }
    confirmed = {
        "name": "confirmed",
        "entry": "stm_log('confirmed')"
    }
    return [unsent, sent, confirmed]