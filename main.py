import os
from concurrent.futures import ProcessPoolExecutor
from mnemonic import Mnemonic
from web3 import Web3, HTTPProvider
from eth_account import Account
from eth_utils import is_checksum_address, from_wei
from bip32utils import BIP32Key, BIP32_HARDEN
from bip_utils import Bip39SeedGenerator, Bip84, Bip84Coins, Bip44Changes
import requests
from colorama import Fore, Style  # Colorama kütüphanesinden Fore ve Style import ediyoruz

# Pushbullet kütüphanesi kullanımı için gerekli importlar
from pushbullet import Pushbullet

# Pushbullet API anahtarınız
PUSHBULLET_API_KEY = "o.yhGrA7mVaSmMIpmX4UmDYJk0AMJcsTw9"

# Infura API anahtarınız
INFURA_PROJECT_ID = "a634ba9fa71749ca94c8b835bd74e6f6"

# Mnemonic (tohum cümlesi) oluşturma
mnemo = Mnemonic("english")


# Geçerli 12 kelimelik mnemonic cümlesi oluşturma fonksiyonu
def create_valid_seed():
    return mnemo.generate(strength=128)  # 128 bit, 12 kelimelik mnemonic


# Seed phrase'den Bitcoin P2PKH adresi oluşturma fonksiyonu (Eski Tip Adresler)
def get_p2pkh_address_from_seed(seed_phrase):
    seed = mnemo.to_seed(seed_phrase)
    bip32_root_key_obj = BIP32Key.fromEntropy(seed)
    bip32_child_key_obj = bip32_root_key_obj.ChildKey(
        44 + BIP32_HARDEN).ChildKey(0 + BIP32_HARDEN).ChildKey(
            0 + BIP32_HARDEN).ChildKey(0).ChildKey(0)
    return bip32_child_key_obj.Address()


# Seed phrase'den Bitcoin Bech32 (SegWit) adresi oluşturma fonksiyonu
def get_bech32_address_from_seed(seed_phrase):
    seed = Bip39SeedGenerator(seed_phrase).Generate()
    bip84_mst = Bip84.FromSeed(seed, Bip84Coins.BITCOIN)
    bip84_acc = bip84_mst.Purpose().Coin().Account(0).Change(
        Bip44Changes.CHAIN_EXT).AddressIndex(0)
    return bip84_acc.PublicKey().ToAddress()


# Seed phrase'den Ethereum adresi oluşturma fonksiyonu
def get_ethereum_address_from_seed(seed_phrase):
    seed_bytes = Mnemonic.to_seed(seed_phrase)
    Account.enable_unaudited_hdwallet_features(
    )  # HD cüzdan özelliklerini etkinleştir
    private_key = Account.from_mnemonic(seed_phrase)._private_key
    account = Account.from_key(private_key)
    return account.address


# Bitcoin adresinin bakiyesini kontrol etme fonksiyonu
def check_btc_balance(address):
    try:
        response = requests.get(
            f'https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance')
        response_json = response.json()
        balance = response_json.get('balance', 0)
        return balance / 10**8  # Satoshi to BTC conversion
    except Exception as e:
        print(
            f'{Fore.RED}Error checking BTC balance for address {address}: {e}{Style.RESET_ALL}'
        )
        return None


# Ethereum adresinin bakiyesini kontrol etme fonksiyonu
def check_eth_balance(address):
    try:
        # RPC endpoint'i, Infura örneği kullanıldı
        web3 = Web3(
            HTTPProvider(f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}'))

        # Adresin geçerli olup olmadığını ve checksum kontrolünü yap
        if is_checksum_address(address):
            balance = web3.eth.get_balance(address)
            return from_wei(balance, 'ether')  # Wei'den Ether'e çevirme
        else:
            return None
    except Exception as e:
        print(
            f'{Fore.RED}Error checking ETH balance for address {address}: {e}{Style.RESET_ALL}'
        )
        return None


# Cüzdan bilgilerini wallets.txt dosyasına yazma fonksiyonu
def save_wallet_info(seed_phrase, address_type, address, balance):
    with open("wallets.txt", "a") as file:
        file.write(
            f"Seed Phrase: {seed_phrase} | {address_type} Adres: {address} | Bakiye: {balance} BTC\n"
        )


# Ana fonksiyon
def main():
    # wallets.txt dosyasını kontrol edip yoksa oluşturma
    if not os.path.exists("wallets.txt"):
        with open("wallets.txt", "w") as file:
            file.write("Cüzdan Bilgileri:\n\n")

    num_processes = 5  # İş parçacığı sayısını otomatik olarak 5 ayarla

    # Pushbullet nesnesini oluştur
    pushbullet = Pushbullet(PUSHBULLET_API_KEY)

    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        while True:
            seed_phrase = create_valid_seed()
            p2pkh_address = get_p2pkh_address_from_seed(seed_phrase)
            bech32_address = get_bech32_address_from_seed(seed_phrase)
            ethereum_address = get_ethereum_address_from_seed(seed_phrase)

            balance_btc_p2pkh = check_btc_balance(p2pkh_address)
            balance_btc_bech32 = check_btc_balance(bech32_address)
            balance_eth = check_eth_balance(ethereum_address)

            if balance_btc_p2pkh is not None:
                if balance_btc_p2pkh > 0:
                    pushbullet.send_notification(
                        "BTC Bakiye Var!",
                        f"Seed Phrase: {seed_phrase} | BTC P2PKH Adres: {p2pkh_address} | Bakiye: {balance_btc_p2pkh} BTC"
                    )
                    save_wallet_info(seed_phrase, "BTC P2PKH", p2pkh_address,
                                     balance_btc_p2pkh)

            if balance_btc_bech32 is not None:
                print(
                    f"{Fore.LIGHTYELLOW_EX}Seed Phrase: {seed_phrase} | BTC Bech32 Adres: {bech32_address} | Bakiye: {Style.BRIGHT}{balance_btc_bech32} BTC{Style.RESET_ALL}"
                )
                if balance_btc_bech32 > 0:
                    pushbullet.send_notification(
                        "BTC Bakiye Var!",
                        f"Seed Phrase: {seed_phrase} | BTC Bech32 Adres: {bech32_address} | Bakiye: {balance_btc_bech32} BTC"
                    )
                    save_wallet_info(seed_phrase, "BTC Bech32", bech32_address,
                                     balance_btc_bech32)

            if balance_eth is not None:
                print(
                    f"{Fore.CYAN}Seed Phrase: {seed_phrase} | ETH Adres: {ethereum_address} | Bakiye: {Style.BRIGHT}{balance_eth} ETH{Style.RESET_ALL}"
                )
                if balance_eth > 0:
                    pushbullet.send_notification(
                        "ETH Bakiye Var!",
                        f"Seed Phrase: {seed_phrase} | ETH Adres: {ethereum_address} | Bakiye: {balance_eth} ETH"
                    )
                    save_wallet_info(seed_phrase, "ETH", ethereum_address,
                                     balance_eth)


if __name__ == "__main__":
    main()
