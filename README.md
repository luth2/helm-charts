# Helm Chart Repo for EccoSP Charts

![ECCoSP](https://www.entsoe.eu/assets/graphics/uploads/ecco-sp-logo.png)

ENTSO-E Communication & Connectivity Service Platform (ECCo SP) is a standardized communication platform for the Energy market. It contains ECP (Energy Communication Platform) and EDX (ENTSO-E Data Exchange) as a software solution for establishing communication between TSOs.

## ECCo SP Security Feature

ECCo SP is a software for creating a secure, centrally managed network for data exchange. With ECCo SP, business applications can confidently exchange data with other organizations that are part of the same network. Unlike traditional methods like SFTP, SMTP, and MFT, ECCo SP automatically manages the PKI (Public Key Infrastructure) and allows only authorized participants to communicate. Additionally, ECCo SP stands apart from AS4 by being centrally governed and allowing for endpoints to be placed within a protected network zone, ensuring that they are shielded from external threats.

The key features of ECCo SP:

* All messaging offers Confidentiality, Authentication, Integrity and Non-Repudiation.
* The network can be scaled to support High Availability.
* Access to the network is restricted through a registration process and controlled centrally. Compromised endpoints can be excluded from the network.
* Secure Software Development Lifecycle, which guarantees regular vulnerability scanning, continuous updating of the software and immediate patching if necessary.

## ECP – Energy Communication Platform

![ECP](https://www.entsoe.eu/assets/graphics/uploads/thumbnail_0a1abssgsdcolbaj.png)

The purpose of the ECP is to provide message delivery capabilities with the following additional key features: Security, Reliability, Integration, Standard, Transparency, and Portability. ECP supports several integration channels such as AMQP(S), MADES Web Service (IEC 62325-504), and FSSF (File System Shared Folder).

ECP contains three components :

* The client component - ECP Endpoint
* The service provider components - ECP Component Directory and ECP Broker

## EDX – ENTSO-E Data Exchange

![EDX](https://www.entsoe.eu/assets/graphics/uploads/thumbnail_5y7u5lpwyjwcs4rm.png)

EDX is an additional and optional extension of ECP.

EDX is the communication platform for OPDE applications. It creates a distributed service platform where both service providers and consumers are connected via a state-of-the-art communication platform. It allows using additional integration channels for messaging. While ECP uses a fixed set of integration channels, EDX allows using (S)FTP, FSSP, MADES, SCP, or Web Services (e.g.: IEC 62325-504).

EDX also allows the implementation of new integration channels easily. It creates the basis for the OPDE platform and other ENTSO-E applications in the future that require reliable and secure communication.

EDX contains two components :

* The client component - EDX Toolbox
* The service provider component - EDX Service Catalogue
