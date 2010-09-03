#!/usr/bin/env python
#coding:utf-8
# Author: Marco Mescalchin --<>
# Purpose: Post withings scale data to myfitnesspal
# Created: 30/08/2010

from mechanize import Browser
from datetime import datetime
import simplejson as json
from decimal import Decimal
from ConfigParser import ConfigParser
import sys,os

iniFile = os.path.join(sys.path[0],"mywt2myfp.ini")

#######################################################################
class MyFitnessPal:

    # Browser Object
    br = Browser()
    br.set_handle_robots(False)

    #----------------------------------------------------------------------
    def __init__(self,user,passwd):
        """Constructor"""
        self.user = user
        self.passwd = passwd
        self.login()

    def logResponse(self,name,response):
        f = file("%s.log.html" % name,'w')
        f.write(response.read())
        f.flush()
        f.close()

    def login(self):
        print "Loggin in %s" % self.user
        self.br.open("http://www.myfitnesspal.com/account/login")
        self.br.select_form(nr=0)
        self.br["username"] = self.user
        self.br["password"] = self.passwd
        try:
            self.logResponse("login_response",self.br.submit())
            self.logged_in = True
        except:
            self.logged_in = False

    def checkinWeight(self,weight):
        print "Checkin weight %s" % weight
        self.br.open("http://www.myfitnesspal.com/measurements/check_in")
        self.br.select_form(nr=0)
        self.br["weight[display_value]"] = "%s" % weight
        try:
            self.logResponse("weight_response",self.br.submit())
            return True
        except:
            return False

class myWithings:

    # Browser Object
    br = Browser()
    br.set_handle_robots(False)

    # Status Codes
    statusCodes = {
        0:'Operation was successfull',
        2555:'An unknown error occured',
        247:'The userid is either absent or incorrect',
        249:'Boh',
        250:'The userid and publickey provided do not match, or the user does not share its data',
        293:'The callback URL is either absent or incorrect',
        304:'The comment is either absent or incorrect'
    }


    url = "http://wbsapi.withings.net/%(service_name)s?action=%(action_name)s&%(parameters)s"

    def __init__(self,w_id,w_key):
        """Constructor"""
        self.w_id = w_id
        self.w_key = w_key

    def getmeas(self,last_date_stamp,meastype=1):
        "Example: http://wbsapi.withings.net/measure?action=getmeas&userid=29&publickey=b71d95d5fb963458&startdate=1222819200&enddate=1223190167"
        print "Gettin weight from withings api..."
        params = [
            "userid=%s" % self.w_id,
            "publickey=%s" % self.w_key,
            "meastype=%s" % meastype,
            "lastupdate=%s" % last_date_stamp,
            "limit=1"]

        self.br.open(self.url % {'service_name':'measure','action_name':'getmeas','parameters':"&".join(params)})

        self.rs = json.loads(self.br.response().read())

        if self.rs['status'] == 0:
            if len(self.rs['body']['measuregrps']) > 0:
                self.date = datetime.fromtimestamp(self.rs['body']['measuregrps'][0]['date'])
                self.date_stamp = self.rs['body']['updatetime']
                self.weight = Decimal(self.rs['body']['measuregrps'][0]['measures'][0]['value'])/1000
                self.status = self.statusCodes[self.rs['status']]
                print "Weight %s at %s" % (self.weight,self.date)
                return True
            else:
                print "Nothing New"
                self.status = "Nothing New"
                return False
        else:
            self.date = 0
            self.date_stamp = 0
            self.weight = 0
            self.status = self.statusCodes[self.rs['status']]
            print "Error getting weight: %s" % self.status
            return False

if __name__=='__main__':
    # apro il config
    cf = ConfigParser()
    cf.read(iniFile)

    users = cf.sections()

    for u in users:
        if cf.getboolean(u,'enabled'):
            print "Processing user %s" % u
            wt = myWithings(cf.get(u,'w_id'),cf.get(u,'w_key'))
            cf.set(u,'last_check',datetime.now())
            if wt.getmeas(cf.get(u,'w_last')):
                cf.set(u,'w_last',wt.date_stamp)
                cf.set(u,'w_status',wt.status)
                cf.set(u,'w_last_weight',wt.weight)
                mf = MyFitnessPal(cf.get(u,'myfp_login'),cf.get(u,'myfp_passwd'))
                if mf.logged_in:
                    if mf.checkinWeight("%s" % wt.weight):
                        print "ok!"

            else:
                cf.set(u,'w_status',wt.status)
    cf.write(file(iniFile,"w"))
