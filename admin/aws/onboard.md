# Admin Guide:

## First time setup

Admin related setup should be done from a seperate machine, not the raspberry pi. The admin handles adding new users to the app and configuring the AWS resources for the app and each user.

1. Clone the repo:
    ```bash
    git clone https://github.com/pillious/pi-photo-album.git
    cd pi-photo-album/admin/aws
    ```

1. Initialize terraform project
    ```
    terraform init
    ```

1. Create the AWS resources:
    ```bash
    # Dry run to see what will be created
    terraform plan
    ```

    ```bash
    terraform apply
    ```

1. Create a `users.txt` file `admin/aws/`

    > [!Tip]
    > This file should contain a list of usernames, one per line. Usernames must be unique, max length of 64 chars, and may only contain [a-zA-Z0-9_-].

    Example:
    ```
    user1
    user2
    user3
    ```

## How to onboard a new user to the app

1. Add a username to the list of users `admin/aws/users.txt`

1. Create the user and resources:
    ```bash
    terraform apply
    ```

1. Get required information for the user:

    > [!Tip]
    > Simplest way is to use `jq` (`sudo apt install jq`) to parse the `admin/aws/terraform.tfstate` file .

    > [!Tip]
    > In the following steps, replace `<username>` username you added in step 1.

    - `AWS_ACCESS_KEY_ID`:
        ```bash
        cat terraform.tfstate | jq -r '.resources[] | select(.type == "aws_ssm_parameter") | .instances[] | select(.index_key == "pi-photo-album-user-<username>") | select(.attributes.id | test("access-key$")) | .attributes.value'
        ```

    - `AWS_SECRET_ACCESS_KEY`:
        ```bash
        cat terraform.tfstate | jq -r '.resources[] | select(.type == "aws_ssm_parameter") | .instances[] | select(.index_key == "pi-photo-album-user-<username>") | select(.attributes.id | test("secret-key$")) | .attributes.value'
        ```

    - `PUSH_QUEUE_URL`:
        ```bash
        cat terraform.tfstate | jq -r '.resources[] | select(.type == "aws_sqs_queue") | .instances[] | select(.attributes.id | test("pi-photo-album-event-queue.fifo$")) | .attributes.id'
        ```

    - `PUSH_QUEUE_ROLE`:
        ```bash
        cat terraform.tfstate | jq -r '.resources[] | select(.type == "aws_iam_role" and .name == "push_event_role") | .instances[] | select(.attributes.id == "pi-photo-album-push-event-role") | .attributes.arn'
        ```

    - `RECEIVE_EVENT_QUEUE_URL`:
        ```bash
        cat terraform.tfstate | jq -r '.resources[] | select(.type == "aws_sqs_queue") | .instances[] | select(.attributes.id | test("<username>-receive-event-queue.fifo$")) | .attributes.id'
        ```