import { SyftSDK} from './sdk.js';

const syftSDK = new SyftSDK();

syftSDK.rpc(
    "syft://shubham@openmined.org/public/rpc",
    {
        'Content-Type': 'application/json',
        'User-Agent': 'MyApp/1.0'
    },
    "Ping!",
);