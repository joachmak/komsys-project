
def get_stm_transitions():
    t0 = {
        "source": "initial",
        "target": "unsent"
    }
    t1 = {
        "source": "unsent",
        "target": "sent",
        "trigger": "click",
        "effect": "stm_request_help"
    }
    t2 = {
        "source": "sent",
        "target": "unsent",
        "trigger": "click",
        "effect": "stm_cancel_help_request"
    }
    t4 = {
        "source": "sent",
        "target": "confirmed",
        "trigger": "sig_claim"
    }
    t5 = {
        "source": "confirmed",
        "target": "sent",
        "trigger": "sig_unclaim"
    }
    t6 = {
        "source": "sent",
        "target": "unsent",
        "trigger": "sig_resolve"
    }
    t7 = {
        "source": "confirmed",
        "target": "unsent",
        "trigger": "sig_resolve"
    }
    return [t0, t1, t2, t4, t5, t6, t7]


def get_stm_states():
    unsent = {
        "name": "unsent",
        "entry": "stm_log('unsent');",
        "sig_receive_request_resolution": "stm_receive_request_resolution"
    }
    sent = {
        "name": "sent",
        "entry": "stm_log('sent')",
        "sig_receive_request_claim": "stm_receive_request_claim",
        "sig_receive_request_resolution": "stm_receive_request_resolution",
        "sig_update_queue_pos": "stm_update_queue_pos"
    }
    confirmed = {
        "name": "confirmed",
        "entry": "stm_log('confirmed')",
        "sig_receive_request_claim": "stm_receive_request_claim",
        "sig_receive_request_resolution": "stm_receive_request_resolution",
        "sig_cancel_claim": "stm_cancel_claim"
    }
    return [unsent, sent, confirmed]
