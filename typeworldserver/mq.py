# project
import typeworldserver
from typeworldserver import classes
from typeworldserver import web

# other
import typeworld
import datetime
import json
from flask import abort, g, Response
from googleapiclient import discovery
from google.cloud import ndb
import time

typeworldserver.app.config["modules"].append("mq")

connectiontests = {}
compute = discovery.build("compute", "v1")


def announceToMQ(parameters):

    parameters["apiKey"] = typeworldserver.secret("MQ_APIKEY")

    for instance in availableMQInstances():
        success, response, responseObject = typeworld.client.request(
            f"http://{instance.ip}:80/publish", parameters, timeout=10
        )
        if type(response) != str:
            response = response.decode()

        if success:
            if response != "ok":
                return False, "announceToMQ(): " + response
        else:
            return False, "announceToMQ(): " + response

    return True, None


def getGCEtemplates(nameFilter=None):
    result = compute.instanceTemplates().list(project="typeworld2").execute()
    instanceTemplates = result["items"] if "items" in result else None
    if instanceTemplates:
        instanceTemplates.sort(
            key=lambda x: datetime.datetime.fromisoformat(x["creationTimestamp"]),
            reverse=True,
        )
        return [
            x
            for x in instanceTemplates
            if (nameFilter is not None and x["name"].startswith(nameFilter)) or nameFilter is None
        ]
    else:
        return []


def instancesPerTemplate(instanceTemplate):
    result = compute.instances().aggregatedList(project="typeworld2").execute()
    zones = result["items"] if "items" in result else None
    if zones:
        for zone in zones:
            if "instances" in zones[zone]:
                for instance in zones[zone]["instances"]:
                    if instance["status"] == "RUNNING":
                        thisTemplate = ("- name: " + instanceTemplate["name"] + "\n") in instance["metadata"]["items"][
                            0
                        ]["value"]
                        if thisTemplate:
                            yield instance


def getGCEinstances(nameFilter=None):
    """
    Actually running MQ instances
    """
    instances = []
    result = compute.instances().aggregatedList(project="typeworld2").execute()
    allInstances = result["items"] if "items" in result else None
    for zone in allInstances:
        if "instances" in allInstances[zone]:
            for instance in allInstances[zone]["instances"]:
                if (nameFilter is not None and instance["name"].startswith(nameFilter)) or nameFilter is None:
                    instances.append(instance)
    return instances


class MQInstance(classes.TWNDBModel):
    """
    Represents a Google Cloud Engine instance running
    https://github.com/typeworld/messagequeue-docker
    """

    ip = web.StringProperty()
    template = web.StringProperty()
    status = web.StringProperty()
    statusJson = web.JsonProperty()
    GCEinstance = web.JsonProperty()
    GCEtemplate = web.JsonProperty()

    def updateStatus(self, GCEinstances):

        for GCEinstance in GCEinstances:
            if GCEinstance["name"] == self.key.id():

                self.status = GCEinstance["status"]

                if GCEinstance["status"] == "RUNNING":
                    success, response, responseObject = typeworld.client.request(
                        f"http://{self.ip}/stats", method="GET", timeout=3
                    )
                    if success:
                        self.statusJson = json.loads(response)
                        self.status = "OK"
                    else:
                        self.status = "UNREACHABLE"

    def delete(self):
        compute.instances().delete(
            project="typeworld2",
            zone=self.GCEinstance["zone"].split("/")[-1],
            instance=self.key.id(),
        ).execute()
        self.key.delete()


def updateMQInstances(GCEtemplates=[], GCEinstances=[]):

    runningKnownMQInstances = []
    availableKnownMQInstances = []
    instancesToDelete = []

    if not GCEtemplates:
        GCEtemplates = getGCEtemplates("messagequeue")
    if not GCEinstances:
        GCEinstances = getGCEinstances("messagequeue")

    knownMQInstances = MQInstance.query().fetch()
    runningKnownMQInstances = []

    for GCEinstance in GCEinstances:
        ip = GCEinstance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
        name = GCEinstance["name"]
        # Template
        template = None
        for GCEtemplate in GCEtemplates:
            if ("- name: " + GCEtemplate["name"] + "\n") in GCEinstance["metadata"]["items"][0]["value"]:
                template = GCEtemplate["name"]
                break

        instance = MQInstance.get_or_insert(name)

        # Create new
        if instance not in knownMQInstances:
            instance.ip = ip
            instance.template = template
            instance.GCEinstance = GCEinstance
            instance.GCEtemplate = GCEtemplate
            instance.updateStatus(GCEinstances)
            instance.put()

        runningKnownMQInstances.append(instance)
        if instance.status == "OK":
            availableKnownMQInstances.append(instance)

    # Check health of previously existing instance
    runningInstanceNames = [x["name"] for x in GCEinstances]
    for instance in knownMQInstances:

        if instance.key.id() in runningInstanceNames:

            # Check only if hasn't been created new in this routine
            instance.updateStatus(GCEinstances)
            instance.put()

            if instance not in runningKnownMQInstances:
                runningKnownMQInstances.append(instance)
                if instance.status == "OK":
                    availableKnownMQInstances.append(instance)

        # Delete
        else:
            instancesToDelete.append(instance)
    print("instancesToDelete:", instancesToDelete)
    ndb.delete_multi([x.key for x in instancesToDelete])

    # instancesToDelete = list(set(knownMQInstances) - set(runningKnownMQInstances))

    return runningKnownMQInstances, availableKnownMQInstances


def availableMQInstances():
    return MQInstance.query(MQInstance.status == "OK").fetch(read_consistency=ndb.STRONG)


@typeworldserver.app.route("/mq", methods=["GET", "POST"])
def list_mqs():

    if not g.admin:
        return abort(401)

    g.html.mediumSeparator()

    g.html.DIV(class_="content")

    g.html.area("MQ Instances")

    GCEtemplates = getGCEtemplates("messagequeue")
    GCEinstances = getGCEinstances("messagequeue")

    g.html.P()
    g.html.T("Amount of new instances to start")
    g.html.textInput("amountOfNewInstances", 1)
    g.html.T("from this template")
    g.html.SELECT(name="templateName", id="templateName")
    for i, instanceTemplate in enumerate(GCEtemplates):
        g.html.OPTION(value=instanceTemplate["id"])
        g.html.T(instanceTemplate["name"])
        if i == 0:
            g.html.T(" (newest)")
        g.html._OPTION()
    g.html._SELECT()

    g.html.T("Numer of CPUs")
    g.html.SELECT(name="cpus", id="cpus")
    for cpu in range(1, 32):
        g.html.OPTION(value=cpu + 1)
        g.html.T(f"{cpu+1} CPUs")
        g.html._OPTION()
    g.html._SELECT()

    g.html.T("GB of Memory")
    g.html.SELECT(name="memory", id="memory")
    for memory in range(16):
        g.html.OPTION(value=(memory + 1) * 1024)
        g.html.T(f"{memory+1} GB")
        g.html._OPTION()
    g.html._SELECT()

    # g.html._P()

    # g.html.P()
    g.html.A(
        class_="button",
        onclick=(
            "AJAX('#action', '/changemqinstance', {'action': 'insert', 'zone':"
            " 'us-east1-b', 'amountOfNewInstances': $('#amountOfNewInstances').val(),"
            " 'templateName': $('#templateName').val(), 'cpus': $('#cpus').val(),"
            " 'memory': $('#memory').val()});"
        ),
    )
    g.html.T("Start New Instances")
    g.html._A()
    g.html._P()

    g.html.separator()

    g.html.TABLE()
    g.html.TR()
    g.html.TH()
    g.html.T("Name")
    g.html._TH()
    g.html.TH()
    g.html.T("Region")
    g.html._TH()
    g.html.TH()
    g.html.T("IP")
    g.html._TH()
    g.html.TH()
    g.html.T("Status")
    g.html._TH()
    g.html.TH()
    g.html.T("Template")
    g.html._TH()
    g.html.TH(style="width: 5%;")
    g.html._TH()
    g.html._TR()

    runningKnownMQInstances, availableKnownMQInstances = updateMQInstances(GCEtemplates, GCEinstances)
    _availableMQInstances = availableMQInstances()

    for instance in runningKnownMQInstances:
        g.html.TR()
        g.html.TD()
        g.html.T(instance.key.id())
        g.html._TD()
        g.html.TD()
        g.html.T(instance.GCEinstance["zone"].split("/")[-1])
        g.html._TD()
        g.html.TD()
        g.html.T(instance.ip)
        g.html._TD()
        g.html.TD()
        if instance in _availableMQInstances:
            g.html.T("🟢 ")
        g.html.T(instance.status)
        if instance.statusJson:
            g.html.BR()
            g.html.T(f"Connections: {instance.statusJson['tcpConnections']}")
            g.html.BR()
            g.html.T(f"Memory: {instance.statusJson['usedMemoryPercentage']}%")
            # g.html.BR()
            # g.html.T(f"Gunicorn Memory: {instance.statusJson['memoryGunicorn']}%")
        g.html._TD()
        g.html.TD()
        g.html.T(instance.template)
        if instance.template == GCEtemplates[0]["name"]:
            g.html.BR()
            g.html.T("(newest)")
        g.html._TD()
        g.html.TD()
        # if instance.status in ("RUNNING", "OK"):
        g.html.A(
            onclick=f"AJAX('#action', '/changemqinstance', {{'action': 'delete', 'name': '{instance.key.id()}'}});"
        )
        g.html.T('<span class="material-icons-outlined">delete</span>')
        g.html._A()
        g.html._TD()
        g.html._TR()
    g.html._TABLE()

    g.html._area()

    g.html.area("Connection Tests")
    g.html.P()
    if connectiontests:
        timestamp = sorted(list(connectiontests.keys()))[-1]
        g.html.T(f"Latest test ({timestamp}) saw {connectiontests[timestamp]} returns.")
    else:
        g.html.T("No test available yet.")
    g.html._P()

    g.html.P()
    g.html.A(
        class_="button",
        onclick="AJAX('#action', '/changemqinstance', {{'action': 'connectiontest'}});",
    )
    g.html.T("Run Test")
    g.html._A()
    g.html._P()

    g.html._area()

    g.html._DIV()

    return g.html.generate()


@typeworldserver.app.route("/changemqinstance", methods=["GET", "POST"])
def startmq():

    # https://developers.google.com/resources/api-libraries/documentation/compute/v1/python/latest/compute_v1.instances.html#insert

    if not g.admin:
        return abort(401)

    g.html.SCRIPT()

    if g.form.get("action") == "delete":
        assert g.form.get("name")
        instance = MQInstance.get_or_insert(g.form.get("name"))
        instance.delete()
        time.sleep(3)

    elif g.form.get("action") == "insert":
        assert g.form.get("zone")
        assert g.form.get("templateName")
        assert int(g.form.get("amountOfNewInstances"))
        assert int(g.form.get("cpus"))
        assert int(g.form.get("memory"))
        name = f"messagequeue-{time.strftime('%Y%m%dt%H%M%S')}"
        for i in range(int(g.form.get("amountOfNewInstances"))):
            config = {
                "name": f"{name}-{g.form.get('cpus')}cpus-{int(int(g.form.get('memory'))/1024)}gb-{i}",
                "machineType": (
                    f"zones/{g.form.get('zone')}/machineTypes/custom-{g.form.get('cpus')}-{g.form.get('memory')}"
                ),
            }
            compute.instances().insert(
                project="typeworld2",
                zone=g.form.get("zone"),
                sourceInstanceTemplate="global/instanceTemplates/" + g.form.get("templateName"),
                body=config,
            ).execute()

        time.sleep(5)

    elif g.form.get("action") == "connectiontest":
        timestamp = int(time.time())
        connectiontests[timestamp] = 0

        parameters = {}
        parameters["topic"] = "connectiontest"
        parameters["command"] = "connectiontest"
        parameters["serverTimestamp"] = timestamp

        success, response = announceToMQ(parameters)

        if not success:
            g.html.T(f"info('{response}');")

    g.html.T("AJAX('#stage', '/mq', {'inline': 'true'});")
    g.html._SCRIPT()

    return g.html.generate()


@typeworldserver.app.route("/registerconnectiontest", methods=["POST"])
def registerconnectiontest():

    # Authorization
    if g.form.get("apiKey"):
        FORMAPIKEY = g.form.get("apiKey").strip()
        if FORMAPIKEY != typeworldserver.secret("MQ_APIKEY"):
            return abort(401)
    else:
        return abort(401)

    connectiontests[int(g.form.get("timestamp"))] += int(g.form.get("receipts"))

    return Response("ok", mimetype="text/plain")
