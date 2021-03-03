# What is Xitoring

> Innovations that makes your daily routine easier

**[Xitoring](https://xitoring.com)**  is an innovative monitoring platform (SaaS) for servers. We bring data from your server using our agent Xitogent to make sure your server is doing fine and avoid any downtime, performance issues, and increasing your customer’s satisfaction.

Our  [global probing nodes](https://xitoring.com/features/)  are always monitoring your servers and as soon as a hiccup is detected, we’ll notify the right contact. We’re continuously working to make our software better and providing incredible features in the future.

Introduced in 2021 to make a revolution in the Server Monitoring industry for whom those are tired of those traditional ways and looking forward to Automation

## Monitoring for Free

Monitor 5 Servers for free, no limited time, no credit cards, You just need to [register](https://app.xitoring.com/register)
 
# What is Xitogent

Xitogent is a python-based and open-source application that is the core of Xitoring, Xitogent can collect data from your servers in an efficient way. it’s very lightweight, easy to install, and configurable.
We are always developing Xitogent to improve and add features, At this time Xitogent has been tested on all major Linux Distros which are the most used OSes in the market.

The Xitogent runs as a service on your server and automatically send your server statistics continuously to your nearest Xitoring’s Server and we use the data to generate graphs or find out if something’s wrong on your server (e.g. we’ll automatically notify you if your CPU or memory usage is above normal).

The Agent runs on a recurring interval and sends statistics to the nearest probe node, we’ll use the data to make sure everything is fine on your server and then use it to make useful graphs (Server Load, CPU Usage, Memory Usage, Disk IO, and Disk Usage).

## What data will Xitogent collect from your Servers?

We only collect data that is necessary for generating Server Graphs and Server Statistics including CPU Usage, Server Load, Memory Usage, Disk IO, Disk Usage, Top processes, Installed Common Softwares, and general details including Hostname and IP Addresses.

## Which OSes are supported?

We support major Linux distributions and we’ll release the Windows Server’s Agent soon.

Xitogent is successfully tested on the following distributions but it’s proofed to work on most major distributions.

 - Centos 6/7/8
 - Fedora 27/30/31/32
 - Redhat 8
 - Ubuntu 14.04/15.04/16.04/18.04/19.04/20.04
 - Debian 5/6/7/8/9/10
 - OpenSuse 15.1

# Installation Manual

Xitogent can be installed using our Installer Script, it will automatically download and set up the environment for Xitogent to work, but the main difference between the automatic installation and manual installation is that when you Install Xitogent with our installer script you will get the binary version set up on your system, but say you want to use the non-binary version, in case of that you need to manually set up everything yourself step by step.

## Installing Python

As we said before, Xitogent is a Python-Based tool so if you want to use the non-binary version you need to have Python installed first.
Xitogent is based on Python 2.7 so it's a better choice to install but Python 3.6 and 3.8 are supported if you have them already installed.

### On CentOS 7 and later

    yum install python2 python2-pip

### On Ubuntu 20.04

    apt install python2 python2-pip

## Install Python libraries

There are 2 main Python dependencies that Xitogent needs to run, **requests** and **psutil**. you can easily install them using **pip**.

    pip install requests
    pip install psutil

## Download and setup Xitogent

Now you need to download `xitogent.py` file and place it somewhere that you think is suitable.

    curl "https://app.xitoring.com/xitogent.py"

### Creating config file

By default, Xitogent uses `/etc/xitogent/xitogent.conf` as the config file so you need to create the directory and the config file within it.

    mkdir /etc/xitogent
    touch /etc/xitogent/xitogent.conf

But you can place the config file somewhere else and point Xitogent to it using `-c` flag for more information check Xitogent help list.

    python xitogent.py -c /path/to/config start

## Register your Server
After setting up everything for Xitogent on your Server, now it's for Xitogent to set up your server for monitoring. for registering your server to the Xitoring App some of the arguments are necessary required:

`register` This argument is used only for the first time and will register/add your server to your Xitoring panel.
`--key` You can find your key from the Xitoring panel > Servers > Add Device modal.
`--auto_update=false` Make sure to disable auto-update because **auto-update is not possible when you are using the non-binary version**.

### Find the Key
In Xitoring App go to the Account page from the sidebar panel, In the right side of that page you can see the the API Access section there is a default API key generated for your account which is the one that is used in the default add device command in Servers page, you either can use that API key or you can create a new one and specify a expire date for it. using each one of those options is your choice.

Below is an example of a complete register command where 4 modules, auto triggers, auto discovery are enabled and auto update is disabled:

    python xitogent.py register --key=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx --module_ftp=ture --module_dns=true --module_http=true --module_ping=true --auto_discovery=true --auto_trigger=true --auto_update=false

You can learn more about Xitogent arguments and params using `xitogent help`

## Start Xitogent

After registering your Server to your panel, you need to start the Xitogent process to gather and send data, for starting Xitogent from the command line you can easily execute:

    python xitogent.py start

## Creating Service for Xitogent

You can manage the Xitogent process with service managers like **systemd** and **SysV**, you need to create a service file based on the service manager that your OS uses.

### systemd Service
The default path for systemd services is:

    /etc/systemd/system/
You can create a service file for Xitogent using:

    vi /etc/systemd/system/xitogent.service
Here is an example of a Xitogent systemd service file content:

    [Unit]
    Description=Xitogent Service
    After=network.target
    
    [Service]
    Type=simple
    ExecStart=/usr/bin/python2 /etc/xitogent/xitogent.py start -c /etc/xitogent/xitogent.conf
    ExecStop=/bin/kill -s TERM $MAINPID
    
    [Install]
    WantedBy=multi-user.target

After creating a service file you need to run the following command to take effect.

    systemctl daemon-reload

### SysV 

For older Linux distros like CentOS 6 there is no **systemd** so you have to stick with the old SysV service manager. using the command below you can download an example of a Xitogent service file for SysV systems:

    curl "https://app.xitoring.com/initd/example.xitogent_service.bash"
    
  Make sure that you place the service file in the correct path which is:

    /etc/init.d/
