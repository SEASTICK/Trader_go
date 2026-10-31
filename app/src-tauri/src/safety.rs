//! Paper-only guard. The app has no broker connection, order API or credential storage, and
//! nothing here may add one. Live trading needs the `pengar-grind` process, not a setting.

pub const TRADING_MODE: &str = "paper";

/// Settings the UI may change. Anything else (e.g. a trading mode or API key) is refused.
pub const ALLOWED_SETTINGS: &[&str] = &["auto_download"];

pub fn check_setting(key: &str, value: &str) -> Result<(), String> {
    if !ALLOWED_SETTINGS.contains(&key) {
        return Err(format!(
            "inställningen '{key}' är inte tillåten i en app som bara kör papper"
        ));
    }
    if key == "auto_download" && value != "true" && value != "false" {
        return Err("auto_download måste vara true eller false".into());
    }
    Ok(())
}

pub fn check_paper_trade(
    symbol: &str,
    side: &str,
    quantity: f64,
    price: f64,
) -> Result<(), String> {
    if symbol.trim().is_empty() || symbol.len() > 32 {
        return Err("symbolen måste vara 1–32 tecken".into());
    }
    if side != "long" && side != "short" {
        return Err("riktningen måste vara long eller short".into());
    }
    if !(quantity.is_finite() && quantity > 0.0 && price.is_finite() && price > 0.0) {
        return Err("antal och pris måste vara positiva tal".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mode_is_paper() {
        assert_eq!(TRADING_MODE, "paper");
    }

    #[test]
    fn trading_mode_and_credentials_cannot_be_set() {
        for key in [
            "trading_mode",
            "mode",
            "api_key",
            "api_secret",
            "broker",
            "live",
        ] {
            assert!(
                check_setting(key, "live").is_err(),
                "{key} should be refused"
            );
        }
        assert!(check_setting("auto_download", "true").is_ok());
        assert!(check_setting("auto_download", "yes").is_err());
    }

    #[test]
    fn paper_trade_inputs_are_validated() {
        assert!(check_paper_trade("BTCUSDT", "long", 0.1, 65000.0).is_ok());
        assert!(check_paper_trade("", "long", 1.0, 1.0).is_err());
        assert!(check_paper_trade("BTC", "buy", 1.0, 1.0).is_err());
        assert!(check_paper_trade("BTC", "long", -1.0, 1.0).is_err());
        assert!(check_paper_trade("BTC", "long", 1.0, f64::NAN).is_err());
    }

    #[test]
    fn app_has_no_network_plugins_or_order_code() {
        let cargo = include_str!("../Cargo.toml");
        for banned in [
            "tauri-plugin-http",
            "tauri-plugin-shell",
            "reqwest",
            "ccxt",
            "binance",
        ] {
            assert!(
                !cargo.contains(banned),
                "Cargo.toml must not depend on {banned}"
            );
        }
        let caps = include_str!("../capabilities/default.json");
        assert!(!caps.contains("shell:") && !caps.contains("http:") && !caps.contains("fs:"));
    }
}
