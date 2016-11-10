# Gandalf Authentication Proxy [![Build Status](https://travis-ci.org/cowboygneox/gandalf.svg?branch=master)](https://travis-ci.org/cowboygneox/gandalf)

![Gandalf Meme: "You shall not pass!"](https://github.com/cowboygneox/gandalf/blob/master/assets/gandalf.jpg?raw=true)

## Explanation

The Gandalf Authentication Proxy manages authentication in your system so that the rest of your system doesn't have to. Motivated by microservice architecture and polyglot aspirations, applying a system-wide authentication filter removes complexity, duplication, and is ultimately more secure due to its simplicity.

## How does it work?

Gandalf acts as a reverse proxy protecting any service that requires **authentication**. A request that does not contain
an appropriate authentication header will be immediately rejected. When a request is appropriately authenticated,
Gandalf will pass the request to the service with two additional headers:

1. `USER_ID`
2. `USERNAME`

The protected service need only concern itself with **authorization** (see [Authentication vs. Authorization](http://serverfault.com/questions/57077/what-is-the-difference-between-authentication-and-authorization)).
If the service needs to know the user, which it certainly will, it can determine the user based on the provided headers.

## Why?

Authentication is often a layer of complexity that interferes with testing and is often reproduced many times in a
system. [Docker](https://www.docker.com/) has driven a new software movement in which we build reusable processes of
software as opposed to reusable libraries, and so Gandalf exists as its own entity, protecting your system from the
evils of the world.

Gandalf also works to reject a user from the system as soon as possible, thus reducing the load unauthorized traffic
will create on your system. Gandalf may not be able to survive record breaking [Denial-of-service attacks](https://en.wikipedia.org/wiki/Denial-of-service_attack),
but it will take a much harder beating than your system can.

**tl;dr:**

1. Gandalf takes care of authentication in an attempt to make testing business functionality much easier to do.
2. Gandalf shuts out unauthorized access so that it doesn't create inappropriate load on your system.
3. Gandalf allows a consistent, scalable layer of authentication that can be applied to many different services.

## How to use it

### Docker Image

The Docker image is hosted [here](https://hub.docker.com/r/cowboygneox/gandalf). It currently binds to port **8888**.

To use the Docker image, configure the following environment variables:

- `GANDALF_PROXIED_HOST`: the *hostname:port* to proxy authenticated requests
- `GANDALF_ALLOWED_HOSTS`: A Python regular expression of hosts that have the ability to change data within Gandalf (usually the same as `GANDALF_PROXIED_HOST`)
- `GANDALF_SIGNING_SECRET`: A secret seed used to ensure that access tokens originate from Gandalf
- `GANDALF_POSTGRES_HOST`: the *hostname* of the PostgreSQL server
- `GANDALF_POSTGRES_USER`: The *user* used to authenticate with PostgreSQL
- `GANDALF_POSTGRES_PASSWORD`: The *password* used to authenticate with PostgreSQL
- `GANDALF_POSTGRES_DB`: The *database* used to store Gandalf data
- `GANDALF_REDIS_HOST`: The *hostanme* of the Redis server

### API Contract

The following endpoints exist for working with Gandalf:

#### `GET /auth/live`

Returns `200 OK` when ready to take requests.

#### `GET /auth/ready`

Returns `200 OK` after confirming that Redis and PostgreSQL are properly configured. Returns `503` w/ an error when
not ready.

#### `POST /auth/login`

Takes a form of credentials (*username & password*) and returns an access token if successfully authenticated.

Example access token response:

    {"access_token": "ZXlKMGVYQWlPaUpLVjFRaUxDSmhiR2NpT2lKSVV6STFOaUo5LmV5SjFjMlZ5U1dRaU9pSTRZVEprTWpZMk5pMDVNR016TFRSaFpqa3RZamsxTUMwNE1HRTRaV0kwTURGaE5HUWlMQ0oxYzJWeWJtRnRaU0k2SW5SbGMzUjFjMlZ5UUcxaWN5SjkuckZlQi1ScXVha3FpLTkxTDJBVjBBM05XNzZ4MW01Y2R5M1hPSm41aGdqVQ=="}

After logging in, to allow use of the system, add the following header to each request:

    Authorization: Bearer {access_token}
    
#### `GET /auth/logout`

Invalidates the provided `access_token`. Attempting to use the system with the same `access_token` will fail for all
future requests.

#### `POST /auth/users/search`

Search for user information (*user_id & username*) by either a list of `user_id` or `username`, but not both. The post
expects a form with one-to-many `user_id`'s or `username`'s.

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### `POST /auth/users/{user_id}/deactivate`

Deactivates the `user_id` from the system immediately. All future requests for that `user_id` will be blocked.

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### `POST /auth/users/{user_id}/reactivate`

Reactivates the `user_id` from the system immediately. The user can immediately reauthenticate and use the system.

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### `GET /auth/users/me`

Returns the `user_id` and `username` currently identified with the `access_token`.

Example response:

    {
        "userId": "3a6bf8d2-32ca-464d-aded-ee2611d673a8",
        "username": "testuser"
    }

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### `GET /auth/users/{user_id}`

Returns the `user_id` and `username` for the requested `user_id`.

Example response:

    {
        "userId": "3a6bf8d2-32ca-464d-aded-ee2611d673a8",
        "username": "testuser"
    }

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.
 
#### `POST /auth/users/{user_id}`
 
Updates the `password` for the current user. `password` is provided as a form value.

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### `POST /auth/users`

Takes a form `username` and `password` and creates a new user. The generated `user_id` is included in the response
header `USER_ID`.

Note: This endpoint is only accessible by hosts that pass the `GANDALF_ALLOWED_HOSTS` regex.

#### Any other request

Requires the header `Authorization: Bearer {access_token}`. If allowed, Gandalf will pass the request verbatim to the 
`GANDALF_PROXIED_HOST`.

### WebSocket Contract

To enable websocket support instead of HTTP support, set the environment variable `GANDALF_WEBSOCKET_MODE=True`.

After the websocket is appropriately authenticated, traffic will proxy as expected. If a user token expires or is
otherwise revoked, the socket will close on the next incoming or outgoing interaction.

To authenticate the websocket, first connect to Gandalf at `/` and immediately provide the following message:

```
Authorization: Bearer {access_token}
```

If authentication fails, the socket will immediately close and return a 401.