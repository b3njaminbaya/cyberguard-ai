CATEGORICAL_FEATURES = ["proto", "service", "state"]

# Every column in UNSW-NB15 except id, the categorical ones above, and the two
# label columns (attack_cat is the target; label is redundant with it).
NUMERIC_FEATURES = [
    "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl",
    "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit",
    "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", "smean",
    "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl",
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm",
    "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm",
    "ct_srv_dst", "is_sm_ips_ports",
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "attack_cat"

# UNSW-NB15's own category set, mapped to a severity a dashboard can act on.
SEVERITY_BY_CATEGORY = {
    "Normal": "none",
    "Worms": "critical",
    "Backdoor": "critical",
    "Shellcode": "critical",
    "DoS": "critical",
    "Exploits": "high",
    "Generic": "high",
    "Reconnaissance": "medium",
    "Analysis": "medium",
    "Fuzzers": "medium",
}
