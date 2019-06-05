# Documentation

- [`linkedin.get_profile`](#get_profile)
- [`linkedin.get_profile_connections`](#get_profile_connections)
- [`linkedin.get_profile_contact_info`](#get_profile_contact_info)

- [`linkedin.get_conversations`](#get_conversations)
- [`linkedin.get_conversation_details`](#get_conversation_details)
- [`linkedin.get_conversation`](#get_conversation)
- [`linkedin.send_message`](#send_message)
- [`linkedin.mark_conversation_as_seen`](#mark_conversation_as_seen)

- [`linkedin.get_current_profile_views`](#get_current_profile_views)

- [`linkedin.get_school`](#get_school)
- [`linkedin.get_company`](#get_company)

- [`linkedin.search`](#search)
- [`linkedin.search_people`](#search_people)

---

<a name="get_profile"></a>

### linkedin.get_profile(public_id=None, urn_id=None)

Returns a Linkedin profile.

**Arguments**
One of:

- `public_id <str>` - public identifier i.e. tom-quirk-1928345
- `urn_id <str>` - id provided by the Linkedin URN

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

profile = linkedin.get_profile('tom-quirk')
```

---

<a name="get_profile_connections"></a>

### linkedin.get_profile(urn_id)

Returns a Linkedin profile's first degree (direct) connections

**Arguments**

- `urn_id <str>` - id provided by the Linkedin URN

**Return**

- `<list>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

connections = linkedin.get_profile_connections('AC000102305')
```

---

<a name="get_profile_contact_info"></a>

### linkedin.get_profile_contact_info(urn_id)

Returns a Linkedin profile's contact information.

**Arguments**
One of:

- `public_id <str>` - public identifier i.e. tom-quirk-1928345
- `urn_id <str>` - id provided by the Linkedin URN

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

profile_info = linkedin.get_profile_contact_info('tom-quirk')
```

---

<a name="get_school"></a>

### linkedin.get_school(public_id)

Returns a school's Linkedin profile.

**Arguments**

- `public_id <str>` - public identifier i.e. university-of-queensland

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

school = linkedin.get_school('university-of-queensland')
```

---

<a name="get_company"></a>

### linkedin.get_company(public_id)

Returns a company's Linkedin profile.

**Arguments**

- `public_id <str>` - public identifier i.e. linkedin

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

company = linkedin.get_company('linkedin')
```

---

<a name="search"></a>

### linkedin.search(params, max_results=None, results=[])

Perform a Linkedin search and return the results.

**Arguments**

- `params <dict>` - search parameters (see implementation of [search_people](#search_people) for a reference)
- `max_results <int> - the max number of results to return

**Return**

- `<list>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

results = linkedin.search({'keywords': 'software'}, 200)
```

---

<a name="get_conversations"></a>

### linkedin.get_conversations()

Return a list of metadata of the user's conversations.

**Return**

- `<list>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

conversations = linkedin.get_conversations()
```

---

<a name="get_conversation"></a>

### linkedin.get_conversation(conversation_urn_id)

Return a conversation

**Arguments**

- `conversation_urn_id <str>` - ID of the conversation

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

conversation = linkedin.get_conversation('6446595445958545408')
```

---

<a name="get_conversation_details"></a>

### linkedin.get_conversation_details(profile_urn_id)

Return the conversation details (metadata) for a given profile_urn_id.
Use this endpoint to get the `conversation id` to send messages (see example).

**Arguments**

- `profile_urn_id <str>` - the urn id of the profile

**Return**

- `<dict>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

profile = linkedin.get_profile('bill-g')
profile_urn_id = profile['profile_id']

conversation_details = linkedin.get_conversation_details(profile_urn_id)
# example: getting the conversation_id
conversation_id = conversation_details['id']
```

---

<a name="send_message"></a>

### linkedin.send_message(conversation_urn_id, message_body)

Sends a message to the given [conversation_urn_id]

**Arguments**

- `conversation_urn_id <str>` - the urn id of the conversation
- `message_body <str>` - the message to send

**Return**

- `<boolean>` - True if error

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

profile = linkedin.get_profile('bill-g')
profile_urn_id = profile['profile_id']

conversation = linkedin.get_conversation_details(profile_urn_id)
conversation_id = conversation['id']

err = linkedin.send_message(conversation_id, "No I will not be your technical cofounder")
if err:
    # handle error
    return
```

---

<a name="mark_conversation_as_seen"></a>

### linkedin.mark_conversation_as_seen(conversation_urn_id)

Mark a given conversation as seen. 

**Arguments**

- `conversation_urn_id <str>` - the urn id of the conversation

**Return**

- `<boolean>` - True if error

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

profile = linkedin.get_profile('bill-g')
profile_urn_id = profile['profile_id']

conversation = linkedin.get_conversation_details(profile_urn_id)
conversation_id = conversation['id']

err = linkedin.mark_conversation_as_seen(conversation_id)
if err:
    # handle error
    return
```

---

<a name="get_current_profile_views"></a>

### linkedin.get_current_profile_views()

Get view statistics for the current profile. Includes views over time (chart data)

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

views = linkedin.get_current_profile_views()
```

---

<a name="search_people"></a>

### linkedin.search_people(keywords=None, connection_of=None, network_depth=None, regions=None, industries=None)

Perform a Linkedin search and return the results.

**Arguments**

- `keywords <str>` - keywords, comma seperated
- `connection_of <str>` - urn id of a profile. Only people connected to this profile are returned
- `network_depth <str>` - the network depth to search within. One of {`F`, `S`, or `O`} (first, second and third+ respectively)
- `regions <list>` - list of Linkedin region ids
- `industries <list>` - list of Linkedin industry ids

**Return**

- `<list>`

**Example**

```python
linkedin = Linkedin(credentials['username'], credentials['password'])

results = linkedin.search_people(
  keywords='software,lol',
  connection_of='AC000120303',
  network_depth='F',
  regions=[4909],
  industries=[29, 1]
)
```
