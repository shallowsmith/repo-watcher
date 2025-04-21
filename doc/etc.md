# MISC

## Setup passwordless sudo
### Step 1 
`sudo visudo`

### Step 2
`USER ALL=(ALL) NOPASSWD: ALL`


## Solve problem for git push on Remote SSH
`sudo chmod 1777 /tmp`
`ps aux | grep git`
`kill -9 12345`
