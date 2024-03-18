import detectEthereumProvider from '@metamask/detect-provider';

const provider = await detectEthereumProvider();

if (provider) {
  startApp(provider);
} else {
  console.log('Please install MetaMask!');
}
function startApp(provider) {
    if (provider !== window.ethereum) {
      console.error('Do you have multiple wallets installed?');
    }
  }
const ethereumButton = document.querySelector('.enableEthereumButton');
const showAccount = document.querySelector('.showAccount');

ethereumButton.addEventListener('click', () => {
  getAccount();
});

async function getAccount() {
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
    .catch((err) => {
      if (err.code === 4001) {
        console.log('Please connect to MetaMask.');
      } else {
        console.error(err);
      }
    });
  const account = accounts[0];
  showAccount.innerHTML = account;
}

