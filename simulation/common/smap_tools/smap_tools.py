from datetime import datetime
import logging
import requests
import pytz

class SmapQuery(object):
    def __init__(self, config={}):
        self._smap = config
        self._smap_enabled = config.get("enabled", False) if type(config) is dict else False

    def get_stream_UUIDs_and_metadata(self, smap_root, stream):
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

    def download_most_recent_point(self, smap_root, stream):
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

        uuids_to_metadata = self.get_stream_UUIDs_and_metadata(smap_root, stream)

        url = smap_root + "/backend/api/query?"
        query = "select data before now limit 1 streamlimit 10 where uuid = '{uuid}'"

        for uuid, metadata in uuids_to_metadata.iteritems():
            timezone = metadata.get("Properties", {}).get("Timezone", None)
            response = requests.post(url, data = query.format(uuid = uuid), verify = False)
            response = response.json()
            readings = response[0]["Readings"]
            if not readings:
                # self._logger.debug("Did not find any readings")
                continue
            ts = readings[0][0]
            val = readings[0][1]
            #divide by 1000 because smap time is in ms and datetime will error because it assumes seconds
            ts /= 1000.0
            ts = datetime.fromtimestamp(ts)
            tz = pytz.timezone(timezone)
            ts = tz.localize(ts)

            # self._logger.debug("ts=\t{ts}\nval=\t{val}".format(ts=ts, val=val))
            if val is None:
                val = float("NaN")

            if not newest_ts or newest_ts < ts:
                newest_ts = ts
                newest_val = val
                newest_uuid = uuid

        # self._logger.debug("Latest info:\tuuid:\t{uuid}\tts:\t{ts}\tval:\t{val}".format(uuid = newest_uuid, ts = newest_ts, val = newest_val))
        return newest_uuid, newest_ts, newest_val
