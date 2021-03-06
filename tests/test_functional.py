# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:expandtab

from __future__ import unicode_literals
import os
from test_muacrypt.test_account import gen_ac_mail_msg
from muacrypt.account import Account
from muacryptcc.plugin import CCAccount
from muacryptcc.filestore import FileStore
from claimchain.utils import bytes2ascii


def test_no_claim_headers_in_cleartext_mail(account_maker):
    acc1, acc2 = account_maker(), account_maker()

    msg = send_mail(acc1, acc2)
    assert not msg['GossipClaims']
    assert not msg['ClaimStore']


def test_claim_headers_in_encrypted_mail(account_maker):
    acc1, acc2 = account_maker(), account_maker()
    send_mail(acc1, acc2)

    dec_msg = send_encrypted_mail(acc2, acc1)[1].dec_msg
    cc2 = get_cc_account(dec_msg['ChainStore'])
    assert dec_msg['GossipClaims'] == cc2.head_imprint
    assert cc2.has_readable_claim(acc1.addr)


def test_claims_contain_keys(account_maker):
    acc1, acc2 = account_maker(), account_maker()
    send_mail(acc1, acc2)

    cc2, ac2 = get_cc_and_ac(send_encrypted_mail(acc2, acc1))
    cc1, ac1 = get_cc_and_ac(send_encrypted_mail(acc1, acc2))

    assert cc1.read_claim_as(cc2, acc2.addr) == bytes2ascii(ac2.keydata)


def test_gossip_claims(account_maker):
    acc1, acc2, acc3 = account_maker(), account_maker(), account_maker()
    send_mail(acc1, acc2)
    send_mail(acc1, acc3)

    cc2, ac2 = get_cc_and_ac(send_encrypted_mail(acc2, acc1))
    cc3, ac3 = get_cc_and_ac(send_encrypted_mail(acc3, acc1))
    cc1, ac1 = get_cc_and_ac(send_encrypted_mail(acc1, [acc2, acc3]))

    assert cc1.read_claim_as(cc2, acc3.addr) == bytes2ascii(ac3.keydata)


# send a mail from acc1 with autocrypt key to acc2
def send_mail(acc1, acc2):
    msg = gen_ac_mail_msg(acc1, acc2)
    acc2.process_incoming(msg)
    return msg


def send_encrypted_mail(sender, recipients):
    """Send an encrypted mail from sender to recipients
       Decrypt and process it.
       Returns the result of processing the Autocrypt header
       and the decryption result.
    """
    if isinstance(recipients, Account):
        recipients = [recipients]
    msg = gen_ac_mail_msg(sender, recipients, payload="hello ä umlaut", charset="utf8")
    enc_msg = sender.encrypt_mime(msg, [r.addr for r in recipients]).enc_msg
    for rec in recipients:
        processed = rec.process_incoming(enc_msg)
        decrypted = rec.decrypt_mime(enc_msg)
    return processed, decrypted


def get_cc_and_ac(pair):
    """
       Claimchain Account corresponding to the CC headers
       and the processed autocrypt header
    """
    processed, decrypted = pair
    return get_cc_account(decrypted.dec_msg['ChainStore']), processed.pah


def get_cc_account(store_dir):
    """ Retrieve a ClaimChain account based from the give store_dir.
    """
    assert os.path.exists(store_dir)
    store = FileStore(store_dir)
    cc_dir = os.path.join(store_dir, '..')
    assert os.path.exists(cc_dir)
    return CCAccount(cc_dir, store)
