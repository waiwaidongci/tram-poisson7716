import {request} from '../api/http.js';

let token = sessionStorage.getItem('analysis-token');
let user = null;

export const session = {
  get actor() { return user; },
  get token() { return token; },
  get canWrite() { return user?.role === 'analyst' || user?.role === 'admin'; },
  get canReview() { return user?.role === 'admin'; },
  async restore() {
    if (!token) return;
    try { user = await request('/auth/me', {token}); }
    catch (error) {
      if (error.status === 401) this.signOut();
      else throw error;
    }
  },
  async signIn(username, password) {
    const info = await request('/auth/login', {body: {username, password}});
    token = info.token;
    user = {username:info.username, role:info.role};
    sessionStorage.setItem('analysis-token', token);
  },
  signOut() {
    user = null;
    token = null;
    sessionStorage.removeItem('analysis-token');
  },
};
