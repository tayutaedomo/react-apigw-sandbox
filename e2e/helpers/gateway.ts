// Gateway Response は Hosting の1 Originを許可する。ローカル・AWS 単体モードは対象外。
export const gatewayTestEnabled = Boolean(process.env.AWS_API_BASE_URL && process.env.HOSTING_BASE_URL);
export const gatewayCorsEnabled = process.env.EXPECT_GATEWAY_CORS !== 'false';
