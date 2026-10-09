// Public configuration only. Never put AppSecret or tokens here.
// For CloudBase, set cloud env/service. An empty baseURL permits private WeChat
// access only; iOS pairing remains unavailable until a production HTTPS URL exists.
// Omit cloud to keep using the existing wx.request HTTPS transport.
module.exports = { baseURL: '' };
