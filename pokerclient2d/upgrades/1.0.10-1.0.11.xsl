<?xml version="1.0" encoding="ISO-8859-1"?><!-- -*- nxml -*- -->

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:func="http://exslt.org/functions"
                xmlns:str="http://exslt.org/strings"
                extension-element-prefixes="str func"
                exclude-result-prefixes="str">

 <xsl:import href="str.replace.function.xsl" />

 <xsl:preserve-space elements="*" />

 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <!--
     Add web server information to edit account with a URL matching the poker server
     if not already present.
 --> 

 <xsl:template match="/settings/servers">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>

  <xsl:if xml:space="preserve" test="not(/settings/web)">
  <xsl:element name="web"><xsl:attribute name="browser">/usr/bin/firefox</xsl:attribute>http://<xsl:value-of select="substring-before(/settings/servers/text(), ':')" />/poker-web/</xsl:element>
  </xsl:if>

 </xsl:template>
 
 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
