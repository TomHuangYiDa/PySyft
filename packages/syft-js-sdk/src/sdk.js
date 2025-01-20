// Configuration object for API settings
const config = {
  proxyUrl: 'http://localhost:8000',
  headers: {
      'Content-Type': 'application/json',
  }
};

// Some example data
const userMessage = {
  content: "can you list the files inside the folder 'super_secret_stuff' in Shubham's datasite",
};

// Example function to demonstrate usage
async function ask(message) {
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

ask(userMessage)
  .then(data => console.log('Got response from server:', data))  // Then use the JSON data
  .catch(error => console.error('Error:', error));