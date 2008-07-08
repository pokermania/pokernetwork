<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <xsl:template match="/server/listen">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
  <xsl:comment>
    <![CDATA[
    <auth script="/usr/local/share/poker-network/pokerauth.py"/>
    ]]>
  </xsl:comment>
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
