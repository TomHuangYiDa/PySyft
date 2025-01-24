// Configuration object for API settings
const config = {
    proxyURL: 'http://localhost:9081',  // should be syftbox.localhost in production
    headers: {
        'Content-Type': 'application/json',
    }
};


class SyftSDK {
    constructor(proxyURL = config.proxyURL) {
        this.proxyURL = proxyURL;
        this.localStorageAvailable = typeof localStorage !== 'undefined';
    }

    /**
     * Store future_id and request_path mapping in localStorage
     * @param {string} futureId - The future ID to store
     * @param {string} requestPath - The request path to associate with the future ID
     * @returns {void}
     */
    storeFutureRequest(futureId, requestPath) {
        if (!this.localStorageAvailable) {
            console.warn(`localStorage is not available. Request ${futureId} will not be stored.`);
            return;
        }
        const futureRequests = JSON.parse(localStorage.getItem('futureRequests') || '{}');
        futureRequests[futureId] = requestPath;
        localStorage.setItem('futureRequests', JSON.stringify(futureRequests));
        console.log("localStorage updated:", localStorage.getItem('futureRequests'));
    }

    /**
     * Get request path for a given future ID from localStorage
     * @param {string} futureId - The future ID to lookup
     * @returns {string|null} The request path or null if not found
     */
    getRequestPath(futureId) {
        if (!this.localStorageAvailable) return null;

        const futureRequests = JSON.parse(localStorage.getItem('futureRequests') || '{}');
        return futureRequests[futureId] || null;
    }

    /**
     * Performs a remote procedure call (RPC) to a Syft endpoint.
     * 
     * @param {string} url - The Syft URL in format syft://email@domain[/path]
     * @param {Object.<string, string>} [headers={}] - HTTP headers to include in the request
     * @param {string|Buffer} [body=''] - Request body to be sent
     * @param {Object} [options={}] - Additional options for the request
     * @param {Object.<string, string>} [options.headers] - Additional headers to merge with request headers
     * 
     * @throws {Error} When the URL format is invalid
     * @throws {Error} When the HTTP request fails
     * 
     * @returns {Promise<Object>} The parsed JSON response from the server
     * 
     * @example
     * const sdk = new SyftSDK('syftbox.localhost');
     * try {
     *   const response = await sdk.rpc(
     *     "syft://<user_email>/public/rpc",
     *     { 'Content-Type': 'application/json', 'User-Agent': 'MyApp/1.0'},
     *     "Ping!",
     *   );
     * } catch (error) {
     *   console.error(error);
     * }
     */
    async rpc(url, headers = {}, body = '', options = {}) {
        const syftUrlPattern = /^syft:\/\/([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(\/.*)?$/;
        if (!syftUrlPattern.test(url)) {
            throw new Error('Invalid SyftBoxURL format. Must be syft://email@domain[/path]');
        }

        const payload = {
            url,
            body: body
        };

        try {
            const response = await fetch(`${this.proxyURL}/rpc`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const response_data = await response.json();

            // fake response data
            // const response_data = {
            //     status: 'pending',
            //     future_id: '01JJB7Z81D9B6F6173VPXE7914',
            //     request_path: '/home/dk/SyftBoxStage/datasites/shubham@openmined.org/public/rpc',
            //     poll_url: '/rpc/status/01JJB7Z81D9B6F6173VPXE7914',
            // }
            console.log('RPC response:', response_data);
            this.storeFutureRequest(response_data.future_id, response_data.request_path);

            return response_data;

        } catch (error) {
            console.error('RPC request failed:', error);
            throw error;
        }
    }

    /**
     * Check the status of an RPC request
     * If the future is pending, keep it in the pending list of localStorage to keep polling (what's the interval?)
     * If the future is errored / resolved / rejected, save it somewhere to show the results and 
     *   remove it from the pending list in localStorage
     * @param {string} request_id - The ID of the request to check
     * @throws {Error} When request_id is not a string or is empty
     */
    async rpc_status(request_id, headers = {}) {
        if (typeof request_id !== 'string') {
            throw new Error('Invalid request_id. Must be a string');
        }
        if (!request_id.trim()) {
            throw new Error('request_id cannot be empty');
        }

        const response = await fetch(`${this.proxyURL}/rpc/status/${request_id}`, {
            method: 'GET',
            headers: headers,
        });
        const response_data = await response.json();
        console.log('RPC status:', response_data);
        return response_data;
    }

}

function showLocalStorage(element_id) {
    const futureRequests = JSON.parse(localStorage.getItem('futureRequests') || '{}');
    const outputDiv = document.getElementById(element_id);

    if (Object.keys(futureRequests).length === 0) {
        outputDiv.innerHTML = `<pre>LocalStorage is empty</pre>`;
        return;
    }

    const formattedContent = Object.entries(futureRequests)
        .map(([futureId, requestPath]) => {
            return `Future ID: ${futureId}\nRequest Path: ${requestPath}`;
        })
        .join('\n\n');

    outputDiv.innerHTML = `
        <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
        <b>LocalStorage Content:</b>
        -----------------
        ${formattedContent}
        </pre>`;
}

function clearLocalStorage(element_id) {
    localStorage.removeItem('futureRequests');
    const outputDiv = document.getElementById(element_id);
    outputDiv.innerHTML = `
        <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
        LocalStorage cleared successfully!
        </pre>`;
}

export { SyftSDK, showLocalStorage, clearLocalStorage };