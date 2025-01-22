// Configuration object for API settings
const config = {
  proxyUrl: 'http://localhost:9081',
  headers: {
      'Content-Type': 'application/json',
  }
};


// Some example data
const humanMessage = {
  content: "can you list the files inside the folder 'super_secret_stuff' in Shubham's datasite",
};

const rpcMessage = {
};

// Send human messages to the server
async function send_message(message) {
  try {
      const response = await fetch(`${config.proxyUrl}/ask`, {
          method: 'POST',
          headers: config.headers,
          body: JSON.stringify(message)
        }
      )
      if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
  } catch (error) {
      console.error('Error sending user data:', error);
      throw error;
  }
}


// send rpc requests to the server
async function send_rpc(rpcMessage) {
  const params = {
    method: 'get',
    datasite: 'khoa@openmined.org',
    path: 'public/apps/chat'
  }
  // const queryString = new URLSearchParams(params).toString();
  // const url = `${config.proxyUrl}/rpc?${queryString}`;
  const url = `${config.proxyUrl}/rpc` + '/' + params.datasite + '/' + params.path;
  console.log('sending url:', url)

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: config.headers,
      // body: JSON.stringify(rpcMessage)
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending user data:', error);
    throw error;
  }
}

async function check_request_status(requestKey) {
  try {
    const url = `${config.proxyUrl}/rpc/status/${requestKey}`
    console.log('sending url:', url)
    const response = await fetch(url, {
      method: 'GET',
      headers: config.headers,
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log('checking request status:', data);
  } catch (error) {
    console.error('Error checking request status:', error);
    throw error;
  }
}


send_message(humanMessage)
  .then(data => console.log('Got response from server:', data))  // Then use the JSON data
  .catch(error => console.error('Error:', error));

send_rpc(rpcMessage)
.then(data => console.log('Got response from server:', data))  // Then use the JSON data
.catch(error => console.error('Error:', error));

check_request_status("abc123")
  .then(data => console.log('Got response from server:', data))  // Then use the JSON data
  .catch(error => console.error('Error:', error));



// todos:
//  1. how to write js sdk
//  2. learn jsdoc typing (important)
//  3. not putting in global scope but window scope (important)
//  4. for SDK, always take objects as input
//  5. browswer storage (localStorage / IndexedDB?)  --> make decision
//  6. what's the configs - one thing is that we know HTTP Proxy runs at https://syftbox.localhost
//  7. create RPC Request / Response object in the JS SDK which sends to the proxy and  
//        reconstructed into RPCRequest and RPCResponse objects
//  8. The rpc.send needs a client to be included in the call. How the JS SDK knows which client
//      is sending the request if there are multiple clients running in one machine?
// 9. Does the RPC 
// 10. Should we keep the SDK JS oritented, like how `fetch` was called (just functions), 
//      or should we write the SDK as a class and take objects as inputs?
// what are we using to serialize the Request / Response objects (protobuf / JSON)
// can we use TypeScript, or just using JSDoc

// class SyftSDK {
//   constructor(config) {
//     this.config = config;
//   }

//   async send_message(message) {
//     try {
//         const response = await fetch(`${this.config.proxyUrl}/ask`, {
//             method: 'POST',
//             headers: this.config.headers,
//             body: JSON.stringify(message)
//           }
//         )
//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }
//         const data = await response.json();
//         return data;
//     } catch (error) {
//         console.error('Error sending user data:', error);
//         throw error;
//     }
//   }

//   // async send_rpc(rpcMessage) {
//   //   const params = {
//   //     method: 'get',
//   //     datasite: 'khoa@openmined.org',

// }