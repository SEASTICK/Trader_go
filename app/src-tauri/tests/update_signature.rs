//! Checks the signature format the updater relies on, the same way tauri-plugin-updater does:
//! base64-wrapped minisign public key and signature, verified with `minisign-verify`.
//! Fixtures were signed with a throwaway key whose private half was deleted.

use base64::{engine::general_purpose::STANDARD, Engine};
use minisign_verify::{PublicKey, Signature};

fn decode(b64: &str) -> String {
    String::from_utf8(STANDARD.decode(b64.trim()).unwrap()).unwrap()
}

fn verify(pubkey_b64: &str, sig_b64: &str, data: &[u8]) -> bool {
    let key = PublicKey::decode(&decode(pubkey_b64)).unwrap();
    let sig = Signature::decode(&decode(sig_b64)).unwrap();
    key.verify(data, &sig, true).is_ok()
}

const PUB: &str = include_str!("fixtures/test.pub");
const SIG: &str = include_str!("fixtures/update.bin.sig");
const DATA: &[u8] = include_bytes!("fixtures/update.bin");

#[test]
fn signed_update_verifies() {
    assert!(verify(PUB, SIG, DATA));
}

#[test]
fn tampered_update_is_rejected() {
    let mut data = DATA.to_vec();
    data[0] ^= 1;
    assert!(!verify(PUB, SIG, &data));
}

#[test]
fn update_signed_by_another_key_is_rejected() {
    assert!(!verify(include_str!("fixtures/other.pub"), SIG, DATA));
}

/// Verifies a real build artifact. Set both variables to run it, e.g. after `tauri build`:
/// TRADERGO_VERIFY_FILE=<bundle>.app.tar.gz TRADERGO_VERIFY_PUBKEY=<key.pub> cargo test --test update_signature
#[test]
fn verify_artifact_from_env() {
    let (Ok(file), Ok(pubkey)) = (
        std::env::var("TRADERGO_VERIFY_FILE"),
        std::env::var("TRADERGO_VERIFY_PUBKEY"),
    ) else {
        return;
    };
    let data = std::fs::read(&file).unwrap();
    let sig = std::fs::read_to_string(format!("{file}.sig")).unwrap();
    let key = std::fs::read_to_string(pubkey).unwrap();
    assert!(
        verify(&key, &sig, &data),
        "signature check failed for {file}"
    );
    let mut tampered = data.clone();
    let mid = tampered.len() / 2;
    tampered[mid] ^= 1;
    assert!(!verify(&key, &sig, &tampered));
}
