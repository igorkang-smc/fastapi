import { useEffect } from 'react';
import { gapi } from 'gapi-script';

const GoogleLoginButton = () => {
  useEffect(() => {
    const loadGoogleScript = () => {
      gapi.load('auth2', () => {
        gapi.auth2.init({ client_id: '576963665063-b0as1vrt1f4cmgrk5j7t2pjh2iqaj2mg.apps.googleusercontent.com' });
      });
    };
    loadGoogleScript();
  }, []);

  const handleLogin = () => {
    const auth2 = gapi.auth2.getAuthInstance();
    auth2.signIn().then((googleUser) => {
      const idToken = googleUser.getAuthResponse().id_token;
      // Send the ID token to the backend
      fetch('/api/auth/google-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_token: idToken }),
      })
        .then(response => response.json())
        .then(data => {
          // Handle response, typically storing the JWT token
          localStorage.setItem('access_token', data.access_token);
        })
        .catch(err => console.error(err));
    });
  };

  return <button onClick={handleLogin}>Login with Google</button>;
};

export default GoogleLoginButton;