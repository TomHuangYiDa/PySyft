import { SyftSDK} from './sdk.js';

const syftSDK = new SyftSDK();

// syftSDK.rpc(
//     "syft://shubham@openmined.org/public/rpc",
//     {
//         'Content-Type': 'application/json',
//         'User-Agent': 'MyApp/1.0'
//     },
//     "Ping!",
// );

syftSDK.rpc_status(
    "01JJBA98HA2022VZMJP5PS3PWT",
)

