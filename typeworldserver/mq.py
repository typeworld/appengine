# project
import typeworldserver
from typeworldserver import classes
from typeworldserver import web
from typeworldserver import helpers

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

    # TODO:
    # check for instance availability,
    # queue message & spin up new instance if necessary

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
            if (nameFilter is not None and x["name"].startswith(nameFilter))
            or nameFilter is None
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
                        thisTemplate = (
                            "- name: " + instanceTemplate["name"] + "\n"
                        ) in instance["metadata"]["items"][0]["value"]
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
                if (
                    nameFilter is not None and instance["name"].startswith(nameFilter)
                ) or nameFilter is None:
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


@typeworldserver.app.route("/mqinstancestarted", methods=["POST"])
def MQInstanceStarted():
    """
    Feedback call, run on startup of MQ instance
    """
    if g.form.get("apiKey") == typeworldserver.secret("MQ_APIKEY"):

        runningKnownMQInstances, availableKnownMQInstances = updateMQInstances()
        if len(runningKnownMQInstances) == len(availableKnownMQInstances):
            helpers.email(
                "hq@mail.type.world",
                ["tech@type.world"],
                "MQ spinup successful",
                "MQ spinup successful",
            )
        else:
            helpers.email(
                "hq@mail.type.world",
                ["tech@type.world"],
                "MQ spinup not successful",
                "After the new instance called /mqinstancestarted, the number of known"
                " instances was still different than the number of available"
                f" instances.\n\nAll instances:\n{runningKnownMQInstances}\n\nAvailable"
                f" instances:\n{availableKnownMQInstances}",
            )

        currently_spinning_up_new_mq_instance = classes.Preference.query(
            classes.Preference.name == "currentlySpinningUpNewMQInstance"
        ).get()
        currently_spinning_up_new_mq_instance.content = "False"
        currently_spinning_up_new_mq_instance.put()

        # TODO:
        # unload all queued messages here

        return Response("ok", mimetype="text/plain")


def startMQInstance():
    """
    Get list of all known running MQ instances (including unreachable), as well as available (reachable) instances
    """
    runningKnownMQInstances, availableKnownMQInstances = updateMQInstances()

    currently_spinning_up_new_mq_instance = classes.Preference.query(
        classes.Preference.name == "currentlySpinningUpNewMQInstance"
    ).get()

    if not availableKnownMQInstances:
        if currently_spinning_up_new_mq_instance.content == "False":
            startinstance()


def updateMQInstances(GCEtemplates=[], GCEinstances=[]):
    """
    Return list of all known running MQ instances (including unreachable), as well as available (reachable) instances
    """

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
            # print(GCEtemplate["name"], GCEinstance["metadata"]["items"])
            for item in GCEinstance["metadata"]["items"]:
                # print(item["value"], "- name: " + GCEtemplate["name"] + "\n" in item["value"])
                if "- name: " + GCEtemplate["name"] + "\n" in item["value"]:
                    template = GCEtemplate["name"]
                    break
            # print(template, "\n\n")

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
    # print("instancesToDelete:", instancesToDelete)
    ndb.delete_multi([x.key for x in instancesToDelete])

    # instancesToDelete = list(set(knownMQInstances) - set(runningKnownMQInstances))

    return runningKnownMQInstances, availableKnownMQInstances


def availableMQInstances():
    return MQInstance.query(MQInstance.status == "OK").fetch(
        read_consistency=ndb.STRONG
    )


@typeworldserver.app.route("/mq", methods=["GET", "POST"])
def list_mqs():

    if not g.admin:
        return abort(401)

    currently_spinning_up_new_mq_instance = classes.Preference.query(
        classes.Preference.name == "currentlySpinningUpNewMQInstance"
    ).get()

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

    g.html.T("Machine Type")
    g.html.SELECT(name="machineType", id="machineType")
    for key, name in (
        ("e2-micro", "E2 Micro (.25-2 CPU, 1GB RAM)"),
        ("e2-small", "E2 Small (.5-2 CPU, 2GB RAM)"),
        ("e2-medium", "E2 Medium (.5-2 CPU, 4GB RAM)"),
        ("custom", "Custom"),
    ):
        g.html.OPTION(value=key)
        g.html.T(name)
        g.html._OPTION()
    g.html._SELECT()

    g.html.T("Number of CPUs (Custom Only)")
    g.html.SELECT(name="cpus", id="cpus")
    for cpu in range(1, 32):
        g.html.OPTION(value=cpu + 1)
        g.html.T(f"{cpu+1} CPUs")
        g.html._OPTION()
    g.html._SELECT()

    g.html.T("GB of Memory (Custom Only)")
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
            " 'machineType': $('#machineType').val(),"
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

    runningKnownMQInstances, availableKnownMQInstances = updateMQInstances(
        GCEtemplates, GCEinstances
    )
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
        if instance.status in ("OK", "UNREACHABLE"):
            g.html.A(
                onclick=(
                    "AJAX('#action', '/changemqinstance', {'action': 'delete',"
                    f" 'name': '{instance.key.id()}'}});"
                )
            )
        g.html.T('<span class="material-icons-outlined">delete</span>')
        g.html._A()
        g.html._TD()
        g.html._TR()
    g.html._TABLE()

    g.html.separator()
    g.html.P()
    g.html.T("Currently spinning up new instance(s): ")
    g.html.T(currently_spinning_up_new_mq_instance.content)
    g.html._P()

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


def startinstance(
    zone="us-east1-b",
    templateName=getGCEtemplates("messagequeue")[0]["id"],
    amountOfNewInstances=1,
    machineType="e2-micro",
    cpus=None,
    memory=None,
):

    currently_spinning_up_new_mq_instance = classes.Preference.query(
        classes.Preference.name == "currentlySpinningUpNewMQInstance"
    ).get()
    currently_spinning_up_new_mq_instance.content = "True"
    currently_spinning_up_new_mq_instance.put()

    # https://developers.google.com/resources/api-libraries/documentation/compute/v1/python/latest/compute_v1.instances.html#insert

    config = {}
    name = f"messagequeue-{time.strftime('%Y%m%dt%H%M%S')}"
    for i in range(int(g.form.get("amountOfNewInstances"))):
        if machineType != "custom":
            config["name"] = f"{name}-{machineType}-{i}"
            config[
                "machineType"
            ] = f"zones/{g.form.get('zone')}/machineTypes/{machineType}"
        else:
            config[
                "name"
            ] = f"{name}-{g.form.get('cpus')}cpus-{int(int(g.form.get('memory'))/1024)}gb-{i}"
            config[
                "machineType"
            ] = f"zones/{g.form.get('zone')}/machineTypes/custom-{g.form.get('cpus')}-{g.form.get('memory')}"

        compute.instances().insert(
            project="typeworld2",
            zone=g.form.get("zone"),
            sourceInstanceTemplate="global/instanceTemplates/"
            + g.form.get("templateName"),
            body=config,
        ).execute()


@typeworldserver.app.route("/changemqinstance", methods=["GET", "POST"])
def startmq():

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
        assert (
            g.form.get("machineType") != "custom"
            or int(g.form.get("cpus"))
            and int(g.form.get("memory"))
        )

        startinstance(
            g.form.get("zone"),
            g.form.get("templateName"),
            int(g.form.get("amountOfNewInstances")),
            g.form.get("machineType"),
            int(g.form.get("cpus")),
            int(g.form.get("memory")),
        )

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
