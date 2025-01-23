// Configuration object for API settings
const config = {
  proxyUrl: 'http://localhost:9081',
  headers: {
      'Content-Type': 'application/json',
  }
};


class SyftSDK {
    constructor(baseUrl = config.proxyUrl) {
        this.baseUrl = baseUrl;
    }

    async rpc(url, headers = {}, body = '', options = {}) {
      const syftUrlPattern = /^syft:\/\/([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(\/.*)?$/;
      if (!syftUrlPattern.test(url)) {
          throw new Error('Invalid SyftBoxURL format. Must be syft://email@domain[/path]');
      }
  
    const payload = {
        url,
        headers,
        body: body ? Buffer.from(body).toString('hex') : null,
    };

    try {
        const response = await fetch(`${this.baseUrl}/rpc`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        response = await response.json();
        console.log('response:', response);
        return response;
    } catch (error) {
        console.error('RPC request failed:', error);
        throw error;
    }
  }

}

export { SyftSDK };