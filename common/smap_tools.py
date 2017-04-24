from datetime import datetime
import logging
import requests
import time
import pytz
import uuid 

logging.basicConfig()
logger = logging.getLogger()

def get_stream_UUIDs_and_metadata(smap_root, stream):
    """
        Returns a map of uuid to some metadata (currently just path and timezone)
    """
    query = "select uuid, Properties/Timezone where Path = '{s}'".format(s = stream)
    url = smap_root + "/backend/api/query?"
    
    response = requests.post(url, data = query, verify = False)
    response = response.json()
    uuids_to_metadata = {}
    for stream_data in response:
        uuids_to_metadata[stream_data["uuid"]] = stream_data
        
    return uuids_to_metadata


def download_most_recent_point(smap_root, stream):
    """
        Returns the latest point from a stream path.  Latest means point with timestamp closest to present
        time without being from the future.  It does not mean the most recent point uploaded to the stream
        although in practice those two might often be the same.
        
        Sinnce there can potentially be multiple uuids for any given stream path it returns the uuid and 
        point from the latest point before now.  Takes timezones into account since there is the off chance 
        that a stream could have multiple uuids with different timezones.
        
        returns the uuid of the stream with the latest point, a timezone aware datetime, and a float
    """
    newest_ts = None
    newest_val = None
    newest_uuid = None
     
    uuids_to_metadata = get_stream_UUIDs_and_metadata(smap_root, stream)
    
    url = smap_root + "/backend/api/query?"
    query = "select data before now limit 1 streamlimit 10 where uuid = '{uuid}'"
 
    for uuid, metadata in uuids_to_metadata.iteritems():
        timezone = metadata.get("Properties", {}).get("Timezone", None)
        response = requests.post(url, data = query.format(uuid = uuid), verify = False)
        response = response.json()
        readings = response[0]["Readings"]
        if not readings:
            logger.debug("Did not find any readings")
            continue
        ts = readings[0][0]
        val = readings[0][1]
        #divide by 1000 because smap time is in ms and datetime will error because it assumes seconds
        ts /= 1000.0
        ts = datetime.fromtimestamp(ts)
        tz = pytz.timezone(timezone)
        ts = tz.localize(ts)
        
        logger.debug("ts=\t{ts}\nval=\t{val}".format(ts=ts, val=val))        
        if val is None:
            val = float("NaN")
         
        if not newest_ts or newest_ts < ts:
            newest_ts = ts
            newest_val = val
            newest_uuid = uuid            
            
    logger.debug("Latest info:\tuuid:\t{uuid}\tts:\t{ts}\tval:\t{val}".format(uuid = newest_uuid, ts = newest_ts, val = newest_val))
    return newest_uuid, newest_ts, newest_val


def get_everything_to_post_except_timeseries(source_name, path, obj_uuid, timezone = "US/Pacific", units="kW", additional_metadata={}):
    """
        This function deals with handling all the metadata.  i.e. everything that isn't a (timestamp, value) pair.
        Since one of the fields is actually called "metadata" I am going to refer to the entire collection as headers for this
        function
    """

    headers = {path: {}}

    headers[path]["Metadata"] = {}
    if source_name:
        headers[path]["Metadata"]["SourceName"] = source_name

    if additional_metadata:
        for k, v in additional_metadata.iteritems():
            headers[path]["Metadata"][k] = v

    headers[path]["Properties"] = {}
    headers[path]["Properties"]["Timezone"] = timezone
    headers[path]["Properties"]["ReadingType"] = "double"
    headers[path]["Properties"]["UnitofMeasure"] = units

    if obj_uuid:
        headers[path]["uuid"] = obj_uuid
    else:
        headers[path]["uuid"] = str(uuid.uuid4())

    return headers


def get_data_to_post(everything_except_timeseries_dict, path, timeseries):
    res = everything_except_timeseries_dict
    for ndx in xrange(len(timeseries)):
        timeseries[ndx][0] = int(timeseries[ndx][0])
    res[path]["Readings"] = timeseries

    return res

def chunk_list(lst, num_elements_in_sublist):
    return [lst[i:i + num_elements_in_sublist] for i in range(0, len(lst), num_elements_in_sublist)]


def _upload(readings, url, api_key, source_name, path, obj_uuid, units="kW", additional_metadata={},
           doRobustUpload=True):
    logger.debug("Starting smap upload sourcename: {sn} path: {p} ".format(sn = source_name, p = path))
    logger.debug("Trying to upload:\nfirst_point:\t{d_start}\nlast_point:\t{d_end}".format(d_start=readings[0],
                                                                                           d_end=readings[-1]))
    to_smap_time = lambda x: 1000 * time.mktime(x.timetuple())
    # try parsing to smap time.  If it fails assume the timestamps are already in the expect time (unix time in ms)
    try:
        to_smap_time(readings[0][0])
        readings = [[to_smap_time(i[0]), float(i[1])] for i in readings]
    except Exception as e:
        pass

    headers = get_everything_to_post_except_timeseries(source_name, path, obj_uuid, units, additional_metadata)
    data_to_post = get_data_to_post(headers, path, readings)

    if url[-1] == "/":
        url = url[:-1]

    res = requests.post("{base}/backend/add/{api}".format(base=url, api=api_key), json=data_to_post)
    success = res.status_code == requests.codes.ok

    if success or not doRobustUpload:
        logger.debug("Successfully uploaded data")
        return success

    logger.debug(
        "Posting data to smap in one file failed.  Attempting to split the file into smaller pieces and post individually.")

    # if we are here than the upload failed.  Try breaking it into smaller chunks and post those with repetition in case of failure
    nPoints = 20000
    chunks = chunk_list(readings, nPoints)
    maxAttempts = 10

    for chunk in chunks:
        logger.debug("Posting file with %i points to smap path %s." % (len(chunk), path))
        attempt = 1
        success = False
        while not success:
            data_to_post = get_data_to_post(headers, path, chunk)
            res = requests.post("{base}/backend/add/{api}".format(base=url, api=api_key), json=data_to_post)
            success = res.status_code == requests.codes.ok

            if not success:
                logger.debug(
                    "Posting file with {ct} points to smap failed.  Attempt: {t}".format(ct=len(chunk), t=attempt))
                if attempt > maxAttempts:
                    logger.debug("Posting file with {ct} points to smap failed on all {t} attempts.  Aborting.".format(
                        ct=len(chunk), t=attempt))
                    return False
                else:
                    attempt += 1

    return True

def convert_time_stamp_to_epoch(timestamp):
    return time.mktime(timestamp.timetuple())


def smap_post(smap_root, smap_api_key, stream, units, reading_type, readings, source_name, time_zone, additional_metadata = {}):
    try:
        if not hasattr(smap_post, "cached_uuids"):
            smap_post.cached_uuids = {}

        stream_uuid = smap_post.cached_uuids.get((smap_root, source_name, stream), None)

        if not stream_uuid:
            uuid_to_metadata = get_stream_UUIDs_and_metadata(smap_root, stream, source_name, smap_api_key)
            
            # if there is no cached uuid check the server.  If the server has some just use the first
            # otherwise generate a new UUID
            if uuid_to_metadata:
                stream_uuid = uuid_to_metadata.keys()[0]
            else:
                stream_uuid = str(uuid.uuid4())

        #add whatever was just found or created to the local cache
        smap_post.cached_uuids[(smap_root, source_name, stream)] = stream_uuid

        try:
            logger.debug("trying to upload {stream}".format(stream=stream))
            res = _upload(readings, smap_root, smap_api_key, source_name, stream, stream_uuid, units,
                         additional_metadata=additional_metadata)
            return res
        except Exception as e:
            logger.warning("Error posting to smap: {e}".format(e=e))
            logger.warning(stream)
            logger.warning(units)
            logger.warning(reading_type)
            logger.warning(readings)
    except Exception as e:
        logger.warning("Outer loop error posting to smap: {e}".format(e=e))
        logger.warning(units)
        logger.warning(reading_type)
        logger.warning(readings)
